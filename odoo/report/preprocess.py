# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from lxml import etree

rml_parents = ['tr','story','section']
html_parents = ['tr','body','div']
sxw_parents = ['{http://openoffice.org/2000/table}table-row','{http://openoffice.org/2000/office}body','{http://openoffice.org/2000/text}section']
odt_parents = ['{urn:oasis:names:tc:opendocument:xmlns:office:1.0}body','{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-row','{urn:oasis:names:tc:opendocument:xmlns:text:1.0}section']


class report(object):
    def preprocess_rml(self, root_node,type='pdf'):
        _regex1 = re.compile("\[\[(.*?)(repeatIn\(.*?\s*,\s*[\'\"].*?[\'\"]\s*(?:,\s*(.*?)\s*)?\s*\))(.*?)\]\]")
        _regex11= re.compile("\[\[(.*?)(repeatIn\(.*?\s*\(.*?\s*[\'\"].*?[\'\"]\s*\),[\'\"].*?[\'\"](?:,\s*(.*?)\s*)?\s*\))(.*?)\]\]")
        _regex2 = re.compile("\[\[(.*?)(removeParentNode\(\s*(?:['\"](.*?)['\"])\s*\))(.*?)\]\]")
        _regex3 = re.compile("\[\[\s*(.*?setTag\(\s*['\"](.*?)['\"]\s*,\s*['\"].*?['\"]\s*(?:,.*?)?\).*?)\s*\]\]")
        for node in root_node:
            if node.tag == etree.Comment:
                continue
            if node.text or node.tail:
                def _sub3(txt):
                    n = node
                    while n.tag != txt.group(2):
                        n = n.getparent()
                    n.set('rml_tag', txt.group(1))
                    return "[[ '' ]]"
                def _sub2(txt):
                    if txt.group(3):
                        n = node
                        try:
                            while n.tag != txt.group(3):
                                n = n.getparent()
                        except Exception:
                            n = node
                    else:
                        n = node.getparent()
                    n.set('rml_except', txt.group(0)[2:-2])
                    return txt.group(0)
                def _sub1(txt):
                    if len(txt.group(4)) > 1:
                        return " "
                    match = rml_parents
                    if type == 'odt':
                        match = odt_parents
                    if type == 'sxw':
                        match = sxw_parents
                    if type =='html2html':
                        match = html_parents
                    if txt.group(3):
                        group_3 = txt.group(3)
                        if group_3.startswith("'") or group_3.startswith('"'):
                            group_3 = group_3[1:-1]
                        match = [group_3]
                    n = node
                    while n.tag not in match:
                        n = n.getparent()
                    n.set('rml_loop', txt.group(2))
                    return '[['+txt.group(1)+"''"+txt.group(4)+']]'
                t = _regex1.sub(_sub1, node.text or node.tail)
                if t == " ":
                    t = _regex11.sub(_sub1, node.text  or node.tail)
                t = _regex3.sub(_sub3, t)
                node.text = _regex2.sub(_sub2, t)
            self.preprocess_rml(node,type)
        return root_node

if __name__=='__main__':
    node = etree.XML('''<story>
    <para>This is a test[[ setTag('para','xpre') ]]</para>
    <blockTable>
    <tr>
        <td><para>Row 1 [[ setTag('tr','tr',{'style':'TrLevel'+str(a['level']), 'paraStyle':('Level'+str(a['level']))}) ]] </para></td>
        <td>Row 2 [[ True and removeParentNode('td') ]] </td>
    </tr><tr>
        <td>Row 1 [[repeatIn(o.order_line,'o')]] </td>
        <td>Row 2</td>
    </tr>
    </blockTable>
    <p>This isa test</p>
</story>''')
    a = report()
    result = a.preprocess_rml(node)
    print etree.tostring(result)
