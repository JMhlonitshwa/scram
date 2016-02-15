#!/usr/bin/env bash

set -ev

# Assuming that path contains the built binaries.
# And this script is called from the root directory.
which scram
which scram_tests

scram_tests --gtest_filter=-*Performance*
nosetests -w ./tests/

if [[ -z "${RELEASE}" && "$CXX" = "g++" ]]; then
  nosetests --with-coverage -w ./scripts/
else
  nosetests -w ./scripts/
fi

./scripts/fault_tree_generator.py -b 200 -c 5
scram --graph fault_tree.xml
dot -q -Tsvg Autogenerated_root.dot -o fault_tree.svg
rm fault_tree.xml fault_tree.svg Autogenerated_root.dot
