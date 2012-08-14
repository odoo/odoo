
from pyquery import PyQuery as pq
import re

def html_sanitize(x):
    if not x:
        return x
    root = pq("<div />")
    if type(x) == str:
        x = unicode(x, "utf8", "replace")
    root.html(x)
    result = handle_element(root[0])
    new = pq(result)
    return new.html()

to_remove = set(["script", "head", "meta", "title", "link", "img"])
to_unwrap = set(["html", "body"])

javascript_regex = re.compile("""^\s*javascript\s*\:.*$""")
def handle_a(el, new):
    href = el.get("href", "#")
    if javascript_regex.search(href):
        href = "#"
    new.set("href", href)
special = {
    "a": handle_a,
}

def handle_element(el):
    if type(el) == str or type(el) == unicode:
        return [el]
    if el.tag in to_remove:
        return []
    if el.tag in to_unwrap:
        return reduce(lambda x,y: x+y, [handle_element(x) for x in children(el)])
    new = pq("<%s />" % el.tag)[0]
    for i in children(el):
        append_to(handle_element(i), new)
    if el.tag in special:
        special[el.tag](el, new)
    return [new]
    
def children(el):
    res = []
    if el.text is not None:
        res.append(el.text)
    for i in el.getchildren():
        res.append(i)
        if i.tail is not None:
            res.append(i.tail)
    return res

def append_to(new_ones, el):
    for i in new_ones:
        if type(i) == str or type(i) == unicode:
            children = el.getchildren()
            if len(children) == 0:
                el.text = i
            else:
                children[-1].tail = i
        else:
            el.append(i)