#!/usr/bin/env python

# Blatantly copied from excellent static web site generator stango
# Kudos to Petri Lehtinen for this test runner code =)
#
# Find more about stango here: http://digip.org/stango

import sys
from optparse import OptionParser

try:
    from coverage import coverage
except ImportError:
    coverage = None

parser = OptionParser()
parser.add_option('-v', '--verbose', action='store_true',
                  help='Be more verbose')
if coverage:
    parser.add_option('-c', '--coverage', action='store_true',
                      help='Measure code coverage')

options, args = parser.parse_args()
if args:
    parser.print_help()
    sys.exit(2)

if coverage and options.coverage:
    cov = coverage()
    cov.start()
elif not coverage and options.coverage:
    print >> sys.stderr, 'Coverage module not found'
    sys.exit(1)

import tests
result = tests.run(options.verbose)

if result.wasSuccessful() and options.coverage:
    exclude = [
        'tirsk.tests',
    ]

    def include_module(name):
        # exclude test code
        for prefix in exclude:
            if name.startswith(prefix):
                return False
        return name.startswith('tirsk')

    cov.stop()
    modules = [
        module for name, module in sys.modules.items()
        if include_module(name)
    ]
    cov.report(modules, file=sys.stdout)
    cov.erase()
