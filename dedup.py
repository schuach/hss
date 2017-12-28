import xml.etree.ElementTree as ET
import copy

ET.register_namespace('marc', 'http://www.loc.gov/MARC21/slim')
ns = {'marc': 'http://www.loc.gov/MARC21/slim'}
tree = ET.parse('tst.xml')
root = tree.getroot()
authors = []

# Dedupliziert records, die von mehreren Verfasserinnen eingereicht wurden
for record in root.findall("./marc:record", ns):
    author = record.find('.//*[@tag="100"]/*[@code="a"]').text
    contr = record.find('.//*[@tag="700"]/*[@code="a"]').text
    if contr in authors:
        root.remove(record)
        print(contr, "::", author)
    else:
        authors.append(author)

tree.write("out.xml", encoding='utf-8', xml_declaration=True)
