"""asciicast records

This module provides functions and classes to manipulate asciicast records. Both v1 and v2
format are supported for decoding. For encoding, only the v2 format is available. The
specification of both formats are available here:
    [1] https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v1.md
    [2] https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md
"""
import abc
import json
from collections import namedtuple
from collections.abc import Iterable, Iterator
from typing import ClassVar


class AsciiCastError(Exception):
    pass


class AsciiCastV2Record(abc.ABC):
    """Generic Asciicast v2 record format"""
    @abc.abstractmethod
    def to_json_line(self):
        raise NotImplementedError

    @classmethod
    def from_json_line(cls, line):
        """Raise AsciiCastError if line is not a valid asciicast v2 record"""
        try:
            json_dict = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AsciiCastError from exc
        if isinstance(json_dict, dict):
            return AsciiCastV2Header.from_json_line(line)
        if isinstance(json_dict, list):
            return AsciiCastV2Event.from_json_line(line)
        truncated_line = line if len(line) < 20 else f'{line[:20]}...'
        raise AsciiCastError(f'Unknown record type: "{truncated_line}"')


def _read_v1_records(data):
    v1_header_attributes = {
        'version',
        'width',
        'height',
        'stdout'
    }
    try:
        json_dict = json.loads(data)
    except json.JSONDecodeError as exc:
        raise AsciiCastError from exc
    missing_attributes = v1_header_attributes - set(json_dict)
    if missing_attributes:
        raise AsciiCastError(f'Missing attributes in asciicast v1 file: {missing_attributes}')

    if json_dict['version'] != 1:
        raise AsciiCastError('This function can only decode asciicast v1 data')

    yield AsciiCastV2Header(2, json_dict['width'], json_dict['height'], None, None)

    if not isinstance(json_dict['stdout'], Iterable):
        raise AsciiCastError('Invalid type for stdout attribute (expected Iterable): '
                             f'{json_dict["stdout"]}')

    time = 0
    for event in json_dict['stdout']:
        try:
            time_elapsed, event_data = event
        except ValueError as exc:
            raise AsciiCastError from exc

        if not isinstance(time_elapsed, (int, float)) or not isinstance(event_data, str):
            raise AsciiCastError(f'Invalid type for event: got object "{event}" but expected '
                                 'type Tuple[Union[int, float], str]')
        time += time_elapsed
        yield AsciiCastV2Event(time, 'o', event_data, None)


def read_records(filename: str) -> Iterator[AsciiCastV2Record]:
    """Yield asciicast v2 records from the file

    The records in the file may themselves be in either asciicast v1 or v2 format (although
    there must be only one record format version in the file).
    Raise AsciiCastError if a record is invalid"""
    try:
        with open(filename) as cast_file:
            for line in cast_file:
                yield AsciiCastV2Record.from_json_line(line)
    except AsciiCastError:
        with open(filename) as cast_file:
            yield from _read_v1_records(cast_file.read())


_AsciiCastV2Theme = namedtuple('AsciiCastV2Theme', ['fg', 'bg', 'palette'])


class AsciiCastV2Theme(_AsciiCastV2Theme):
    """Color theme of the terminal.

    All colors must use the '#rrggbb' format

    fg: default text color
    bg: default background colors
    palette: colon separated list of 8 or 16 terminal colors
    """
    def __new__(cls, fg, bg, palette):
        if cls.is_color(fg):
            if cls.is_color(bg):
                colors = palette.split(':')
                if len(colors) >= 16 and all(cls.is_color(c) for c in colors[:16]):
                    return super().__new__(cls, fg, bg, palette)
                if len(colors) >= 8 and all(cls.is_color(c) for c in colors[:8]):
                    new_palette = ':'.join(colors[:8])
                    return super().__new__(cls, fg, bg, new_palette)
                raise AsciiCastError('Invalid palette: the first 8 or 16 colors must be valid')
            raise AsciiCastError(f'Invalid background color: {bg}')
        raise AsciiCastError(f'Invalid foreground color: {fg}')

    @staticmethod
    def is_color(color):
        if isinstance(color, str) and len(color) == 7 and color[0] == '#':
            try:
                int(color[1:], 16)
            except ValueError:
                return False
            return True
        return False


_AsciiCastV2Header = namedtuple('AsciiCastV2Header', ['version', 'width', 'height', 'theme',
                                                      'idle_time_limit'])


class AsciiCastV2Header(AsciiCastV2Record, _AsciiCastV2Header):
    """Header record

    version: Version of the asciicast file format
    width: Initial number of columns of the terminal
    height: Initial number of lines of the terminal
    theme: Color theme of the terminal
    """
    types: ClassVar[dict] = {
        'version': int,
        'width': int,
        'height': int,
        'theme': (type(None), AsciiCastV2Theme),
        'idle_time_limit': (type(None), int, float)
    }

    def __new__(cls, version, width, height, theme, idle_time_limit=None):
        self = super().__new__(cls, version, width, height, theme, idle_time_limit)
        for attr_name in cls._fields:
            attr = self.__getattribute__(attr_name)
            if not isinstance(attr, cls.types[attr_name]):
                raise AsciiCastError(f'Invalid type for attribute {attr_name}: {type(attr)} '
                                     f'(expected one of {cls.types[attr_name]})')
        if version != 2:
            raise AsciiCastError('Only asciicast v2 format is supported')
        return self

    def to_json_line(self):
        attributes = self._asdict()
        if self.theme is not None:
            attributes['theme'] = self.theme._asdict()
        else:
            del attributes['theme']

        if attributes['idle_time_limit'] is None:
            del attributes['idle_time_limit']

        return json.dumps(attributes, ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line):
        attributes = json.loads(line)
        filtered_attributes = {attr: attributes.get(attr) for attr in AsciiCastV2Header._fields}
        if filtered_attributes['theme'] is not None:
            filtered_attributes['theme'] = AsciiCastV2Theme(**filtered_attributes['theme'])

        return cls(**filtered_attributes)


_AsciiCastV2Event = namedtuple('AsciiCastV2Event', ['time', 'event_type', 'event_data', 'duration'])


class AsciiCastV2Event(AsciiCastV2Record, _AsciiCastV2Event):
    """Event record

    time: Time elapsed since the beginning of the recording in seconds
    event_type: Type 'o' if the data was captured on the standard output of the terminal, type
                'i' if it was captured on the standard input
    event_data: Data captured during the recording
    duration: Duration of the event in seconds (non standard field)
    """
    types: ClassVar[dict] = {
        'time': (int, float),
        'event_type': (str,),
        'event_data': (str,),
        'duration': (type(None), int, float),
    }

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        for attr_name in AsciiCastV2Event._fields:
            attr = self.__getattribute__(attr_name)
            if not isinstance(attr, cls.types[attr_name]):
                raise AsciiCastError(f'Invalid type for attribute {attr_name}: {type(attr)} '
                                     f'(expected one of {cls.types[attr_name]})')
        return self

    def to_json_line(self):
        attributes = [self.time, self.event_type, self.event_data]
        return json.dumps(attributes, ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line):
        try:
            time, event_type, event_data = json.loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            raise AsciiCastError from exc

        return cls(time, event_type, event_data, None)
