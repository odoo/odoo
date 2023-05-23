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


class_regex = re.compile(r"(?<=\.)([^/\n#\)\ \?]*?)(?=([\{#\[]|(\ {)))")  # regex to match classes in stylesheets

xml_regex = re.compile(
    r"((?<=(class=\"))((.|\n)*?)(?=\")|(?<=(class=\'))((.|\n)*?)(?=\'))")  # regex to match classes in xml files /!\ DONT OPTIMIZE IT
dynamic_xml_regex = re.compile(
    r"((?<=(-class=\"))(.*?)(?=\")|(?<=(-class=\'))(.*?)(?=\'))")  # regex to match dynamic classes declarations in xml files

js_r1 = r"((?<=(Class\())|(?<=(classList\.add\())|(?<=(classList\.toggle\()))(.*?)(?=\))"  # match the class methods
js_r2 = r"((?<=className = [\"\'])|(?<=value:[\"\'])|(?<=value : [\"\']))(.*?)(?=[\'\"])"  # match the className = and value :
js_r3 = r"(?<=\.)([a-zA-Z0-9\._]*?)(?=[\'\" ])"  # match everything that looks like a .className
js_regex = re.compile(js_r1 + '|' + js_r2 + '|' + js_r3)

html_regex = re.compile(r"(?<=(class=[\"\']))(.*?)(?=[\"\'])")  # regex to match classes in html files

lib_regex = re.compile(r"(/static/lib)")  # regex to check if we are in a library
lib_regex2 = re.compile(r"(/static/src/libs)")  # regex to check if we are in a library

#  ---------------------------------------FUNCTIONS (chronological order)-----------------------------------------------

'''
search files in 'path' with the extension list : 'extensions' eg ['.css', '.scss', '.sass']
'''


def search(path, extensions):
    results = []

    for root, dirs, files in os.walk(path):
        for file in files:
            if EXCLUDE_LIBRARIES and (lib_regex.search(root) or lib_regex2.search(root)):
                continue
            if file.endswith(tuple(extensions)):
                results.append(os.path.join(root, file))

    return results


'''
find all css or scss files in a project
args :
project_directories : one or multiple comma separated directories 
'''


def find_all_files(project_directories, extensions):
    css_files = []
    project_directories = project_directories.split(',')

    for directory in project_directories:
        directory = directory.strip()  # sanitize input
        css_files.extend(search(directory, extensions))

    return css_files


def find_all_classes(file_list):
    css_classes = {}

    for file in file_list:
        f = open(file, "r")
        content = f.read()
        f.close()
        matches = class_regex.finditer(content)
        for match_number, match in enumerate(matches, start=1):
            classe = match.group().split(':')[0].split(' ')[-1].split('.')[-1].strip()
            if css_classes.get(classe) is None:
                css_classes[classe] = [file]
            elif css_classes.get(classe)[-1] is not file:  # prevent duplicates
                css_classes[classe].append(file)
    return css_classes


def find_all_used_classes(file_list):
    used_classes = {}
    dynamic_classes = {}

    for file in file_list:
        f = open(file, "r")
        content = f.read()
        f.close()

        if file.endswith(".js"):
            matches = js_regex.finditer(content)
        elif file.endswith(".xml"):
            matches = xml_regex.finditer(content)
            dynamic_classes_matches = dynamic_xml_regex.finditer(content)

            for match_number, match in enumerate(dynamic_classes_matches, start=1):
                match_group = match.group().split("#")
                if len(match_group) == 2:
                    match_group = match_group[0].split(' ')
                    for unique_match in match_group:
                        dynamic_classes[unique_match.strip("\"'")] = file
        elif file.endswith(".html"):
            matches = html_regex.finditer(content)

        for match_number, match in enumerate(matches, start=1):
            match_group = re.split(r"\s+|\:", match.group())  # TODO compile before

            for unique_match in match_group:
                classe = unique_match.strip("{} \"'")
                if used_classes.get(classe) is None:
                    used_classes[classe] = [file]
                elif used_classes.get(classe)[-1] is not file:
                    used_classes[classe].append(file)

    return used_classes, dynamic_classes


'''
return all dynamic classes that are not used and the one that are probably used
the dynamic classes could come from the CSS or the XML
'''


def remove_used_dynamic_classes(classes, dynamic_declaration_list):
    unused_classes = classes.copy()
    probably_used_classes = {}

    for i in range(len(classes) - 1, -1, -1):
        classe = classes[i]
        for key in dynamic_declaration_list:  # TODO O(n²) use a binary search ?
            if classe.startswith(key) and key != '':
                probably_used_classes[classe] = key
        if probably_used_classes.get(classe) is not None:
            del unused_classes[i]

    return unused_classes, probably_used_classes


def find_unused_classes(css_classes, struct_classes):
    unused_classes = []

    for classe in css_classes:
        if struct_classes.get(classe) is None and struct_classes.get(classe[1:]) is None:
            unused_classes.append(classe)

    return unused_classes


def classify_unused_classes(unused, file_list):
    zero_used_confirmed = []
    maybe_used = []
    maybe_used_files = {}

    for unused_class in unused:
        deepsearch_results = deep_search(unused_class, file_list)  # longest instruction could be parallelized
        if deepsearch_results.get(unused_class) is None:
            zero_used_confirmed.append(unused_class)
        else:
            maybe_used.append(unused_class)
            maybe_used_files[unused_class] = deepsearch_results.get(unused_class)

    return (zero_used_confirmed, maybe_used, maybe_used_files)


def deep_search(item, file_list):
    used_classes = {}
    regex = re.compile(r"(" + item + ")")

    for file in file_list:
        f = open(file, "r")
        content = f.read()
        f.close()
        matches = regex.finditer(content)
        for match_number, match in enumerate(matches, start=1):
            if used_classes.get(match.group()) is None:
                used_classes[match.group()] = [file]
            elif used_classes.get(match.group())[-1] is not file:
                used_classes[match.group()].append(file)
    return used_classes


def generate_results(zero_used_confirmed, maybe_used, maybe_used_locations, probably_used):
    results_maybe = []
    results_zero = []
    results_probably = []

    for unuse in zero_used_confirmed:
        results_zero.append("\n" + unuse + " from " + str(css_classes[unuse]) + " could not be found anywhere")

    for unuse in maybe_used:
        results_maybe.append(
            "\n" + unuse + " from " + str(css_classes[unuse]) + ' may be used in ' + str(maybe_used_locations.get(unuse)))

    for unuse in probably_used:
        results_probably.append(
            "\n" + unuse + " from " + str(css_classes[unuse]) + ' is probably used dynamically with ' + probably_used.get(
                unuse) + ' in ' + str(
                dynamic_classes.get(probably_used.get(unuse))))

    return results_zero, results_maybe, results_probably


def print_results(results):
    for result in results:
        print(result)


def save_results(results, name):
    f = open(name + ".txt", "w")
    f.writelines(results)
    f.close()


# --------------------------------------------------DRIVER--------------------------------------------------------------


found_css_files = find_all_files(DIRECTORIES, ['.css', '.scss', '.sass'])
print(str(len(found_css_files)) + " style files found")
css_classes = find_all_classes(found_css_files)
print(str(len(css_classes)) + " classes found \n")

found_struct_files = find_all_files(DIRECTORIES, ['.js', '.xml', '.html'])
print(str(len(found_struct_files)) + " structure files found")
struct_classes, dynamic_classes = find_all_used_classes(found_struct_files)
print(str(len(struct_classes)) + " pseudo classes found  \n")
print(str(len(dynamic_classes)) + " dynamic classes found  \n")

unused = find_unused_classes(css_classes, struct_classes)
print(str(len(unused)) + " classes probably unused ; removing the dynamic classes...")
unused_dynamically, probably_used = remove_used_dynamic_classes(unused, dynamic_classes)
print(str(len(unused_dynamically)) + " classes probably unused and " + str(
    len(probably_used)) + " classes are probably used dynamically ; starting "
                          "deep scan...")
zero_used_confirmed, maybe_used, maybe_used_locations = classify_unused_classes(unused_dynamically, found_struct_files)
print(str(len(zero_used_confirmed)) + " classes are not used, " + str(len(maybe_used)) +
      " are probably not used and " + str(len(probably_used)) + " are probably used dynamically "
                                                                "Total : " + str(len(unused)) + "\n")

results_zero, results_maybe, results_probably = generate_results(zero_used_confirmed,
                                                                 maybe_used, maybe_used_locations,
                                                                 probably_used)
if PRINT_RESULTS:
    print_results(results_zero)
    print_results(results_maybe)
    print_results(results_probably)

if SAVE_RESULTS:
    save_results(results_zero, "unused_classes")
    save_results(results_maybe, "maybe_unused_classes")
    save_results(results_probably, "probably_used_classes")
    print("results saved !")

print("Done, use with care, some dynamic classes are not evaluated and could cause some false positive")
