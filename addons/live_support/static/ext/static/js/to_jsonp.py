
import sys
import json

file_name = sys.argv[1]
function_name = sys.argv[2]

with open(file_name) as file_:
    content = file_.read()

print "window.%s(%s);" % (function_name, json.dumps(content))

