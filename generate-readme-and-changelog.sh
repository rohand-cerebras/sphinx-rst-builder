#!/bin/sh

set -x

sphinx-build -q -a -E -b rst -d build/readme docs/readme .
sphinx-build -q -a -E -b rst -d build/changelog docs/changelog .
sphinx-build -q -a -E -b html -d build/examples_html docs/examples build/examples_html
sphinx-build -q -a -E -b rst -d build/examples_rst docs/examples .

sphinx-build -q -a -E -b rst -D rst_preserve_code_block_flags=True -d build/examples_rst2 docs/examples build/examples_rst2
