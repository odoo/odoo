Test RPC2 doc snippets
======================

The snippets from the external documentation are extracted by the few
`test_rpc2_doc.*` files of the current directory. All those files are
actual executable that you can run.

In case you are an odoo employee running Linux Mint, you should go fine
executing the `install_deps.sh` script. It installs all the programming
languages used here along with the libraries we used in the examples.

Javascript Steps
----------------

Install the following dependencies:

	# apt install nodejs npm
	$ cd /tmp
	$ npm install jayson

Reported version on the author's laptop:

	$ node --version
	v12.22.9

Then simply run the tests with `--test-tags .test_rpc2_doc_js`.

Ruby Steps
----------

Install the following dependencies:

	# apt install ruby ruby-xmlrpc

Reported version on the author's laptop:

	$ ruby --version
	ruby 3.1.2p20 (2022-04-12 revision 4491bb740a) [x86_64-linux]

Then simply run the tests with `--test-tags .test_rpc2_doc_ruby`

PHP Steps
---------

Install the following dependencies:

	# apt install php-cli php-dom php-xmlrpc composer
	$ cd /tmp
	$ composer require laminas/laminas-xmlrpc

Reported version on the author's laptop:

	$ php --version
	PHP 8.1.2-1ubuntu2.8 (cli) (built: Nov  2 2022 13:35:25) (NTS)
	Copyright (c) The PHP Group
	Zend Engine v4.1.2, Copyright (c) Zend Technologies
		with Zend OPcache v8.1.2-1ubuntu2.8, Copyright (c), by Zend Technologies

Then simply run the tests with `--test-tags .test_rpc2_doc_php`

Java Steps
----------

Install the following dependencies:

	# apt install openjdk-8-jdk-headless
	$ cp /tmp
	$ wget https://archive.apache.org/dist/ws/xmlrpc/apache-xmlrpc-current-bin.tar.gz
	$ tar --remove-files -xf apache-xmlrpc-current-bin.tar.gz

Reported version on the author's laptop:

	$ javac -version
	javac 1.8.0_352
	$ ls | grep apache-xmlrpc
	apache-xmlrpc-3.1.3

Then simply run the tests with `--test-tags .test_rpc2_doc_java`. The test
takes care of both the compilation and the execution.

SH/cURL Steps
-------------

Install the following dependencies:

	# apt install bash curl jq

Then simply run the tests with `--test-tags .test_rpc2_doc_curl`

