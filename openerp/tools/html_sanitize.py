
from pyquery import PyQuery as pq

def html_sanitize(x):
    root = pq("<div />")
    root.html(x)
    result = handle_element(root[0])
    new = pq(result)
    return new.html()

def handle_element(el):
    if type(el) == str or type(el) == unicode:
        return [el]
    else:
        new = pq("<%s />" % el.tag)[0]
        for i in children(el):
            append_to(handle_element(i), new)
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