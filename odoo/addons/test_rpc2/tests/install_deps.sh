#!/usr/bin/env bash
set -eu -o pipefail
read -p 'apt install node ruby php java curl (yes/[no])? ' prompt
set -v
[[ $prompt == 'yes' || $prompt == 'y' ]] && sudo apt install \
	nodejs npm \
	ruby ruby-xmlrpc \
	php-cli php-dom php-xmlrpc composer \
	openjdk-8-jdk-headless \
	bash curl jq

cd /tmp
npm i jayson
composer require laminas/laminas-xmlrpc
wget https://archive.apache.org/dist/ws/xmlrpc/apache-xmlrpc-current-bin.tar.gz
tar -xf apache-xmlrpc-current-bin.tar.gz
rm apache-xmlrpc-current-bin.tar.gz
