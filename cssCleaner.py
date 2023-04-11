"""
Script that search for all css classes unused in a directory
created on 27/March/2023
by Lou ! (loha)
"""

import os
import re

# --------------------------------------------USER DEFINED PARAMETERS---------------------------------------------------


EXCLUDE_LIBRARIES = True
SAVE_RESULTS = True
PRINT_RESULTS = False
DIRECTORIES = '/home/odoo/src/odoo,/home/odoo/src/enterprise'

# ---------------------------------------------REGEX DECLARATION/COMPILATION--------------------------------------------


classRegex = re.compile(r"(?<=\.)([^/\n#\)\ \?]*?)(?=([\{#\[]|(\ {)))")  # regex to match classes in stylesheets

xmlRegex = re.compile(
    r"((?<=(class=\"))((.|\n)*?)(?=\")|(?<=(class=\'))((.|\n)*?)(?=\'))")  # regex to match classes in xml files /!\ DONT OPTIMIZE IT
dynamicXmlRegex = re.compile(
    r"((?<=(-class=\"))(.*?)(?=\")|(?<=(-class=\'))(.*?)(?=\'))")  # regex to match dynamic classes declarations in xml files

jsR1 = r"((?<=(Class\())|(?<=(classList\.add\())|(?<=(classList\.toggle\()))(.*?)(?=\))"  # match the class methods
jsR2 = r"((?<=className = [\"\'])|(?<=value:[\"\'])|(?<=value : [\"\']))(.*?)(?=[\'\"])"  # match the className = and value :
jsR3 = r"(?<=\.)([a-zA-Z0-9\._]*?)(?=[\'\" ])"  # match everything that looks like a .className
jsRegex = re.compile(jsR1 + '|' + jsR2 + '|' + jsR3)

htmlRegex = re.compile(r"(?<=(class=[\"\']))(.*?)(?=[\"\'])")  # regex to match classes in html files

libRegex = re.compile(r"(/static/lib)")  # regex to check if we are in a library
libRegex2 = re.compile(r"(/static/src/libs)")  # regex to check if we are in a library

#  ---------------------------------------FUNCTIONS (chronological order)-----------------------------------------------

'''
search files in 'path' with the extension list : 'extensions' eg ['.css', '.scss', '.sass']
'''


def search(path, extensions):
    results = []

    for root, dirs, files in os.walk(path):
        for file in files:
            if EXCLUDE_LIBRARIES and (libRegex.search(root) or libRegex2.search(root)):
                continue
            if file.endswith(tuple(extensions)):
                results.append(os.path.join(root, file))

    return results


'''
find all css or scss files in a project
args :
projectDirs : one or multiple comma separated directories 
'''


def findAllFiles(projectDirs, extensions):
    cssFiles = []
    projectDirs = projectDirs.split(',')

    for dir in projectDirs:
        dir = dir.strip()  # sanitize input
        cssFiles.extend(search(dir, extensions))

    return cssFiles


def findAllClasses(fileList):
    cssClasses = {}

    for file in fileList:
        f = open(file, "r")
        content = f.read()
        f.close()
        matches = classRegex.finditer(content)
        for matchNum, match in enumerate(matches, start=1):
            classe = match.group().split(':')[0].split(' ')[-1].split('.')[-1].strip()
            if cssClasses.get(classe) is None:
                cssClasses[classe] = [file]
            elif cssClasses.get(classe)[-1] is not file:  # prevent duplicates
                cssClasses[classe].append(file)
            # TODO replace sanitizing by a regex
    return cssClasses


def findAllUsedClasses(fileList):
    usedClasses = {}
    dynamicClasses = {}

    for file in fileList:
        f = open(file, "r")
        content = f.read()
        f.close()

        if file.endswith(".js"):
            matches = jsRegex.finditer(content)
        elif file.endswith(".xml"):
            matches = xmlRegex.finditer(content)
            dynamicClassesMatches = dynamicXmlRegex.finditer(content)

            for matchNum, match in enumerate(dynamicClassesMatches, start=1):
                matchGroup = match.group().split("#")
                if len(matchGroup) == 2:
                    matchGroup = matchGroup[0].split(' ')
                    for uniqueMatch in matchGroup:
                        dynamicClasses[uniqueMatch.strip("\"'")] = file
        elif file.endswith(".html"):
            matches = htmlRegex.finditer(content)

        for matchNum, match in enumerate(matches, start=1):
            matchGroup = re.split(r"\s+|\:", match.group())  # TODO compile before

            for uniqueMatch in matchGroup:
                classe = uniqueMatch.strip("{} \"'")
                if usedClasses.get(classe) is None:
                    usedClasses[classe] = [file]
                elif usedClasses.get(classe)[-1] is not file:
                    usedClasses[classe].append(file)

    return usedClasses, dynamicClasses


'''
return all dynamic classes that are not used and the one that are probably used
the dynamic classes could come from the CSS or the XML
'''


def removeUsedDynamicClasses(classes, dynamicDeclarationList):
    unusedClasses = classes.copy()
    probablyUsedClasses = {}

    for i in range(len(classes) - 1, -1, -1):
        classe = classes[i]
        for key in dynamicDeclarationList:  # TODO O(n²) use a binary search ?
            if classe.startswith(key) and key != '':
                probablyUsedClasses[classe] = key
        if probablyUsedClasses.get(classe) is not None:
            del unusedClasses[i]

    return unusedClasses, probablyUsedClasses


def findUnusedClasses(cssClasses, structClasses):
    unusedClasses = []

    for classe in cssClasses:
        if structClasses.get(classe) is None and structClasses.get(classe[1:]) is None:
            unusedClasses.append(classe)

    return unusedClasses


def classifyUnusedClasses(unused, fileList):
    zeroUseConfirmed = []
    maybeUsed = []
    maybeUsedFiles = {}

    for unusedClass in unused:
        deepRes = deepSearch(unusedClass, fileList)  # longest instruction could be parallelized
        if deepRes.get(unusedClass) is None:
            zeroUseConfirmed.append(unusedClass)
        else:
            maybeUsed.append(unusedClass)
            maybeUsedFiles[unusedClass] = deepRes.get(unusedClass)

    return (zeroUseConfirmed, maybeUsed, maybeUsedFiles)


def deepSearch(item, fileList):
    usedClasses = {}
    regex = re.compile(r"(" + item + ")")

    for file in fileList:
        f = open(file, "r")
        content = f.read()
        f.close()
        matches = regex.finditer(content)
        for matchNum, match in enumerate(matches, start=1):
            if usedClasses.get(match.group()) is None:
                usedClasses[match.group()] = [file]
            elif usedClasses.get(match.group())[-1] is not file:
                usedClasses[match.group()].append(file)
    return usedClasses


def generateResults(zeroUseConfirmed, maybeUsed, maybeUsedLocations, probablyUsed):
    resultsMaybe = []
    resultsZero = []
    resultsProbably = []

    for unuse in zeroUseConfirmed:
        resultsZero.append("\n" + unuse + " from " + str(cssClasses[unuse]) + " could not be found anywhere")

    for unuse in maybeUsed:
        resultsMaybe.append(
            "\n" + unuse + " from " + str(cssClasses[unuse]) + ' may be used in ' + str(maybeUsedLocations.get(unuse)))

    for unuse in probablyUsed:
        resultsProbably.append(
            "\n" + unuse + " from " + str(cssClasses[unuse]) + ' is probably used dynamically with ' + probablyUsed.get(
                unuse) + ' in ' + str(
                dynamicClasses.get(probablyUsed.get(unuse))))

    return resultsZero, resultsMaybe, resultsProbably


def printResults(results):
    for result in results:
        print(result)


def saveResults(results, name):
    f = open(name + ".txt", "w")
    f.writelines(results)
    f.close()


# --------------------------------------------------DRIVER--------------------------------------------------------------


foundCssFiles = findAllFiles(DIRECTORIES, ['.css', '.scss', '.sass'])
print(str(len(foundCssFiles)) + " style files found")
cssClasses = findAllClasses(foundCssFiles)
print(str(len(cssClasses)) + " classes found \n")

foundStructFiles = findAllFiles(DIRECTORIES, ['.js', '.xml', '.html'])
print(str(len(foundStructFiles)) + " structure files found")
structClasses, dynamicClasses = findAllUsedClasses(foundStructFiles)
print(str(len(structClasses)) + " pseudo classes found  \n")
print(str(len(dynamicClasses)) + " dynamic classes found  \n")

unused = findUnusedClasses(cssClasses, structClasses)
print(str(len(unused)) + " classes probably unused ; removing the dynamic classes...")
unusedDynamically, probablyUsed = removeUsedDynamicClasses(unused, dynamicClasses)
print(str(len(unusedDynamically)) + " classes probably unused and " + str(
    len(probablyUsed)) + " classes are probably used dynamically ; starting "
                         "deep scan...")
zeroUseConfirmed, maybeUsed, maybeUsedLocations = classifyUnusedClasses(unusedDynamically, foundStructFiles)
print(str(len(zeroUseConfirmed)) + " classes are not used, " + str(len(maybeUsed)) +
      " are probably not used and " + str(len(probablyUsed)) + " are probably used dynamically "
                                                               "Total : " + str(len(unused)) + "\n")

resultsZero, resultsMaybe, resultsProbably = generateResults(zeroUseConfirmed,
                                                             maybeUsed, maybeUsedLocations,
                                                             probablyUsed)
if PRINT_RESULTS:
    printResults(resultsZero)
    printResults(resultsMaybe)
    printResults(resultsProbably)

if SAVE_RESULTS:
    saveResults(resultsZero, "unusedCssClasses")
    saveResults(resultsMaybe, "maybeUnusedCssClasses")
    saveResults(resultsProbably, "probablyUsedCssClasses")
    print("results saved !")

print("Done, use with care, some dynamic classes are not evaluated and could cause some false positive")
