from __future__ import absolute_import, with_statement

import os
import collections
import xml.etree.ElementTree as ET
import six

if 'OrderedDict' in dir(collections):
    odict = collections
else:
    import ordereddict as odict


class InvalidOFXStructureException(Exception):
    pass


class OfxData(object):
    def __init__(self, tag):
        self.nodes = odict.OrderedDict()
        self.tag = tag
        self.data = ""

    def add_tag(self, name):
        name = name.lower()
        if name not in self.nodes:
            self.nodes[name] = OfxData(name.upper())
            return self.nodes[name]
        elif not isinstance(self.nodes[name], list):
            self.nodes[name] = [self.nodes[name], OfxData(name.upper())]
        else:
            self.nodes[name].append(OfxData(name.upper()))
        return self.nodes[name][-1]

    def del_tag(self, name):
        name = name.lower()
        if name in self.nodes:
            del self.nodes[name]

    def __setattr__(self, name, value):
        if name in self.__dict__ or name in ['nodes', 'tag', 'data', '\
                headers', 'xml']:
            self.__dict__[name] = value
        else:
            self.del_tag(name)
            if isinstance(value, list):
                for val in value:
                    tag = self.add_tag(name)
                    tag.nodes = val.nodes
                    tag.data = val.data
            elif isinstance(value, OfxData):
                tag = self.add_tag(name)
                tag.nodes = value.nodes
                tag.data = value.data
            else:
                tag = self.add_tag(name)
                tag.data = str(value)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        elif name in self.__dict__['nodes']:
            return self.__dict__['nodes'][name]
        else:
            tag = self.add_tag(name)
            return tag

    def __delattr__(self, name):
        if name in self.__dict__:
            del self.__dict__[name]
        elif name in self.__dict__['nodes']:
            del self.__dict__['nodes'][name]
        else:
            raise AttributeError

    def __getitem__(self, name):
        item_list = []
        self.find(name, item_list)
        return item_list

    def find(self, name, item_list):
        for n, child in six.iteritems(self.nodes):
            if isinstance(child, OfxData):
                if child.tag.lower() == name:
                    item_list.append(child)
                child.find(name, item_list)
            else:
                for grandchild in child:
                    if grandchild.tag.lower() == name:
                        item_list.append(grandchild)
                    grandchild.find(name, item_list)

    def __iter__(self):
        for k, v in six.iteritems(self.nodes):
            yield v

    def __contains__(self, item):
        return item in self.nodes

    def __len__(self):
        return len(self.nodes)

    def __str__(self):
        return os.linesep.join("\t" * line[1] + line[0] for line in
                               self.format())

    def format(self):
        if self.data or not self.nodes:
            if self.tag.upper() == "OFX":
                return [["<%s>%s</%s>" % (self.tag, self.data
                        if self.data else "", self.tag), 0]]
            return [["<%s>%s" % (self.tag, self.data), 0]]
        else:
            ret = [["<%s>" % self.tag, -1]]
            for _, child in six.iteritems(self.nodes):
                if isinstance(child, OfxData):
                    ret.extend(child.format())
                else:
                    for grandchild in child:
                        ret.extend(grandchild.format())
            ret.append(["</%s>" % self.tag, -1])

            for item in ret:
                item[1] += 1

            return ret


class OfxUtil(OfxData):
    def __init__(self, ofx_data=None):
        super(OfxUtil, self).__init__('OFX')
        self.headers = odict.OrderedDict()
        self.xml = ""
        if ofx_data:
            if isinstance(ofx_data, six.string_types) and not \
                    ofx_data.lower().endswith('.ofx'):
                self.parse(ofx_data)
            else:
                self.parse(open(ofx_data).read() if isinstance(
                    ofx_data, six.string_types) else ofx_data.read())

    def parse(self, ofx):
        try:
            for line in ofx.splitlines():
                if line.strip() == "":
                    break
                header, value = line.split(":")
                self.headers[header] = value
        except ValueError:
            pass
        finally:
            if "OFXHEADER" not in self.headers:
                self.headers["OFXHEADER"] = "100"
            if "VERSION" not in self.headers:
                self.headers["VERSION"] = "102"
            if "SECURITY" not in self.headers:
                self.headers["SECURITY"] = "NONE"
            if "OLDFILEUID" not in self.headers:
                self.headers["OLDFILEUID"] = "NONE"
            if "NEWFILEUID" not in self.headers:
                self.headers["NEWFILEUID"] = "NONE"

        try:
            tags = ofx.split("<")
            if len(tags) > 1:
                tags = ["<" + t.strip() for t in tags[1:]]

            heirarchy = []
            can_open = True

            for i, tag in enumerate(tags):
                gt = tag.index(">")
                if tag[1] != "/":
                    # Is an opening tag
                    if not can_open:
                        tags[i - 1] = tags[i - 1] + "</" + \
                            heirarchy.pop() + ">"
                        can_open = True
                    tag_name = tag[1:gt].split()[0]
                    heirarchy.append(tag_name)
                    if len(tag) > gt + 1:
                        can_open = False
                else:
                    # Is a closing tag
                    tag_name = tag[2:gt].split()[0]
                    if tag_name not in heirarchy:
                        # Close tag with no matching open, so delete it
                        tags[i] = tag[gt + 1:]
                    else:
                        # Close tag with matching open, but other open
                        # tags that need to be closed first
                        while(tag_name != heirarchy[-1]):
                            tags[i - 1] = tags[i - 1] + "</" + \
                                heirarchy.pop() + ">"
                        can_open = True
                        heirarchy.pop()

            self.xml = ET.fromstringlist(tags)
            self.load_from_xml(self, self.xml)
        except Exception:
            raise InvalidOFXStructureException

    def load_from_xml(self, ofx, xml):
        ofx.data = xml.text
        for child in xml:
            tag = ofx.add_tag(child.tag)
            self.load_from_xml(tag, child)

    def reload_xml(self):
        super(OfxUtil, self).__init__('OFX')
        self.load_from_xml(self, self.xml)

    def write(self, output_file):
        with open(output_file, 'wb') as f:
            f.write(str(self))

    def __str__(self):
        ret = os.linesep.join(":".join(line) for line in
                              six.iteritems(self.headers)) + os.linesep * 2
        ret += super(OfxUtil, self).__str__()
        return ret


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    fixtures = os.path.join(here, '../tests/fixtures/')
    ofx = OfxUtil(fixtures + 'checking.ofx')
#    ofx = OfxUtil(fixtures + 'fidelity.ofx')

    # Manipulate OFX file via XML library
#    for transaction in ofx.xml.iter('STMTTRN'):
#        transaction.find('NAME').text = transaction.find('MEMO').text
#        transaction.remove(transaction.find('MEMO'))
#    ofx.reload_xml()

    # Manipulate OFX file via object tree built from XML
#    for transaction in ofx.bankmsgsrsv1.stmttrnrs.stmtrs.banktranlist.stmttrn:
#        transaction.name = transaction.memo
#        del transaction.memo
#        transaction.notes = "Acknowledged"
    # Modified sytnax for object tree data manipulation
    # I'm using the __getitem__ method like the xml.iter method from
    # ElementTree, as a recursive search
    for transaction in ofx['stmttrn']:
        transaction.name = transaction.memo
        del transaction.memo
        transaction.notes = "Acknowledged"

#    for bal in ofx['bal']:
#        print(bal)

#    ofx.test = "First assignment operation"
#    ofx.test = "Second assignment operation"
#
    print(ofx)

    # Write OFX data to output file
#    ofx.write('out.ofx')

#    for file_name in os.listdir(fixtures):
#        if os.path.isfile(fixtures + file_name):
#            print "Attempting to parse", file_name
#            ofx = OfxParser('fixtures/' + file_name)
#
#            file_parts = file_name.split(".")
#            file_parts.insert(1, 'v2')
#            with open('fixtures/' + ".".join(file_parts), 'wb') as f:
#                f.write(str(ofx))
