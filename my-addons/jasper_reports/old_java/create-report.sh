#!/bin/bash

scriptdir=$(dirname "$0")

if [ "$1" = "--compile" ]; then
	compile="true"
	makejasper="true"
	serverdir="$2"
	report="$3"
	xml="$4"
	output="$5"
	dsn="$6"
	user="$7"
	password="$8"
	params="$9"
else
	compile="false"
	makejasper="true"
	serverdir="$1"
	report="$2"
	xml="$3"
	output="$4"
	dsn="$5"
	user="$6"
	password="$7"
	params="$8"
fi

echo "SERVERDIR: ", $serverdir
echo $compile $makejasper $report $xml $output $dsn $user $password $params
pushd $scriptdir


if [ -z "$JAVA_HOME" ]; then
	directories="/usr/lib/jvm/java-6-sun-1.6.0.10/bin /usr/lib/j2sdk1.6-sun /usr/lib/j2sdk1.5-sun"
	for d in $directories; do
		if [ -d "$d" ]; then
			export JAVA_HOME="$d"
		fi
	done
fi
export PATH="$JAVA_HOME"/bin:/bin:/usr/bin
export CLASSPATH=$(ls -1 lib/* | grep jar$ | awk '{printf "%s:", $1}')
export CLASSPATH="$CLASSPATH":$scriptdir

if [ ! -f "ReportCreator.class" ]; then
	echo "Forcing ReportCreator compilation"
	compile="true"
fi

if [ ! -f "ReportCompiler.class" ]; then
	echo "Compiling ReportCompiler.java ..."
	javac ReportCompiler.java
fi

if [ "$compile" = "true" ]; then
	echo "Compiling ReportCreator.java ..."
	javac ReportCreator.java
fi

if [ "$makejasper" = "true" ]; then
	echo "Creating $report.jasper ..."
	java ReportCompiler "$serverdir/$report.jrxml" "$serverdir/$report.jasper"
fi

echo "Creating report..."
java ReportCreator "$serverdir/$report.jasper" "$xml" "$output" "$dsn" "$user" "$password" "$params"

popd

