# Runbot config

This directory contains configuration files that will be loaded by runbot to define how to run specific tests.

## Parallel testing
The parallel_testing.json file describes how to run the test for all modules in parallel
- starting first subbuild for the at install tests
- then installing a database with all modules
- and finally starting multiple subbuilds to test all post install in parallel.

Note that the test-tags do not use the blacklist, this is to replicate the default odoo --test-enable behaviour. 
Even if a module is blacklisted, it could be installed via an auto_install or if required by another module, and should be tested.
