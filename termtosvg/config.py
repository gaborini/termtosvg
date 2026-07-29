import pkgutil

PKG_TEMPLATE_PATH = 'data/templates'

# Listing templates here is not ideal but importing an on-disk resource lister
# does not seem worth it: it adds startup cost for no functional gain
# ('time termtosvg --help' used to go from 200ms to 350ms when pkg_resources
# was pulled in just to enumerate this directory).
DEFAULT_TEMPLATES_NAMES = [
    'base16_default_dark.svg',
    'dracula.svg',
    'gjm8_play.svg',
    'gjm8_single_loop.svg',
    'gjm8.svg',
    'powershell.svg',
    'progress_bar.svg',
    'putty.svg',
    'solarized_dark.svg',
    'solarized_light.svg',
    'terminal_app.svg',
    'ubuntu.svg',
    'window_frame_js.svg',
    'window_frame_powershell.svg',
    'window_frame.svg',
    'xterm.svg',
]


def validate_geometry(screen_geometry: str) -> tuple[int, int]:
    """Raise ValueError if 'screen_geometry' does not conform to <integer>x<integer> format"""
    columns, rows = (int(value) for value in screen_geometry.lower().split('x'))
    if columns <= 0 or rows <= 0:
        raise ValueError(f'Invalid value for screen-geometry option: "{screen_geometry}"')
    return columns, rows


def default_templates() -> dict[str, bytes]:
    """Return mapping between the name of a template and the SVG template itself"""
    templates = {}
    for template_name in DEFAULT_TEMPLATES_NAMES:
        pkg_template_path = f'{PKG_TEMPLATE_PATH}/{template_name}'
        bstream = pkgutil.get_data(__name__, pkg_template_path)
        templates[template_name.removesuffix('.svg')] = bstream

    return templates
