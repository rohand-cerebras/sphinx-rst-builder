#!/bin/sh

sphinx-build -q -b rst -d build/readme docs/readme .
sphinx-build -q -b rst -d build/changelog docs/changelog .
