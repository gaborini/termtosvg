.PHONY: usage install tests lint build man html deploy_test deploy_prod clean

PYTHON=python3
PIP=$(PYTHON) -m pip

EXAMPLES_DIR=docs/examples
CASTS_DIR=$(EXAMPLES_DIR)/casts

# Version of the manual page tarball. Derived from the package so a release does
# not depend on a CI-provided tag variable.
VERSION=$(shell $(PYTHON) -c 'import termtosvg; print(termtosvg.__version__)')

.DEFAULT_GOAL := usage

usage:
	@echo "Usage:"
	@echo "    make install         # Install the package in editable mode with dev extras"
	@echo "    make tests           # Run unit tests with coverage"
	@echo "    make lint            # Run ruff"
	@echo "    make build           # Build sdist and wheel into dist/"
	@echo "    make man             # Build manual pages (requires pandoc)"
	@echo "    make html            # Render the example gallery under docs/"
	@echo "    make clean           # Remove build artifacts"
	@echo "    make deploy_prod     # Upload distributions to pypi.org"
	@echo "    make deploy_test     # Upload distributions to test.pypi.org"

install:
	$(PYTHON) --version
	$(PIP) install -U -e .[dev]
	$(PIP) freeze

tests:
	coverage run -m unittest termtosvg.tests.suite -v
	coverage report

lint:
	ruff check .

build: clean
	$(PYTHON) -m build
	$(PYTHON) -m twine check --strict dist/*

man:
	pandoc man/termtosvg.md -s -t man > man/termtosvg.man.1
	pandoc man/termtosvg-templates.md -s -t man > man/termtosvg-templates.man.5
	tar -czf "man_$(VERSION).tar.gz" man/termtosvg*.man.*

html:
	cp -r termtosvg/data/templates/ docs/
	termtosvg render $(CASTS_DIR)/awesome.cast $(EXAMPLES_DIR)/awesome_window_frame_powershell.svg -t window_frame_powershell
	termtosvg render $(CASTS_DIR)/awesome.cast $(EXAMPLES_DIR)/awesome_window_frame_js.svg -t window_frame_js
	termtosvg render $(CASTS_DIR)/colors.cast $(EXAMPLES_DIR)/colors_progress_bar.svg -t progress_bar
	termtosvg render $(CASTS_DIR)/htop.cast $(EXAMPLES_DIR)/htop_gjm8.svg -t gjm8
	termtosvg render $(CASTS_DIR)/ipython.cast $(EXAMPLES_DIR)/ipython_window_frame.svg -t window_frame
	termtosvg render $(CASTS_DIR)/unittest.cast $(EXAMPLES_DIR)/unittest_solarized_dark.svg -t solarized_dark
	for template in $$(ls termtosvg/data/templates/*.svg | grep -v gjm8_play); \
	    do \
	    	filename="$$(basename $$template)"; \
		termtosvg render "$(CASTS_DIR)/awesome.cast" "$(EXAMPLES_DIR)/$$filename" -t "$$template"; \
	    done

clean:
	rm -rf build dist *.egg-info

deploy_test:
	$(PYTHON) -m twine upload -r pypitest dist/*

deploy_prod:
	$(PYTHON) -m twine upload -r pypi dist/*
