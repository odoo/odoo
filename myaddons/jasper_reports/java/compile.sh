#!/bin/bash

if [ -z "$JAVA_HOME" ]; then
	directories="/usr/lib/jvm/java-1.8.0-openjdk-amd64/ /usr/lib/jvm/java-8-openjdk-amd64/ /usr/lib/jvm/java-8-openjdk-amd64/lib/tools.jar"
	for d in $directories; do
		if [ -d "$d" ]; then
			export JAVA_HOME="$d"
		fi
	done
fi

echo "JAVA_HOME=$JAVA_HOME"
export PATH="$JAVA_HOME"/bin:/bin:/usr/bin
echo "PATHS=$PATH"
export CLASSPATH=$(ls -1 lib/* | grep jar$ | awk '{printf "%s:", $1}')
export CLASSPATH="$CLASSPATH":$scriptdir
echo "CLASSPATH=$CLASSPATH"

FILES=$(find com -iname "*.java")

javac $FILES || exit

rm -f lib/i18n.jar
rm -f i18n.jar
jar cvf i18n.jar com
mv i18n.jar lib

javac com/nantic/jasperreports/JasperServer.java -Xlint:deprecation -Xlint:unchecked
# javac com/nantic/jasperreports/JasperServer.java
java com.nantic.jasperreports.JasperServer
