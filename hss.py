#!/bin/python3.6
import xml.etree.ElementTree as ET
import os
import datetime

# Namespaces
ET.register_namespace('marc', 'http://www.loc.gov/MARC21/slim')
ns = {'marc': 'http://www.loc.gov/MARC21/slim'}

# Wurzelelment für die Output-Files
template = """
<marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim" 
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
xsi:schemaLocation="http://www.loc.gov/MARC21/slim 
http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd"/>
"""

# Elemente, in die die Datensätze einsortiert werden
el_zug = ET.fromstring(template)
el_nicht = ET.fromstring(template)
gesperrt = ET.fromstring(template)

def make_xpath(tag, ind, subfield):
    """Gibt einen XPATH-Ausdruck als String zurück"""
    if "*" in ind:
        if ind == "**":
            return f'./*[@tag="{tag}"]/*[@code="{subfield}"]'
        elif ind[0] == "*":
            return f'./*[@tag="{tag}"][@ind2="{ind[1]}"]/*[@code="{subfield}"]'
        elif ind[1] == "*":
            return f'./*[@tag="{tag}"][@ind1="{ind[0]}"]/*[@code="{subfield}"]'
    else:
        return f'./*[@tag="{tag}"][@ind1="{ind[0]}"][@ind2="{ind[1]}"]/*[@code="{subfield}"]'


def read_input_files(indir):
    """Liest alle Input-Files und gibt eine Liste mit record-Elmenten (eines pro
    Datensatz) zurück. Wenn eine Arbeit von mehreren Personen eingereicht wurde,
	wird nur ein record hinzugefügt.
    """
    input_dir = indir
    infiles = []
    records = []

    # Liste der Input-Dateien erstellen
    for filename in os.listdir(input_dir):
        infiles.append(os.path.join(input_dir, filename))

    # die einzelen Datensätze deduplizieren und zur Liste records hinzufügen
    for file in infiles:
        tree = ET.parse(file)
        root = tree.getroot()
        for record in root.findall("./marc:record", ns):
            records.append(record)

    return records

def dedup(record_list):
    """Entfernt dublette Datensätze, die dadurch entstehen, dass mehrere
    Personen gemeinsam eine Arbeit verfassen. Nimmt eine Liste von
    record-Elementen als Input und gibt eine deduplizierte Liste zurück.
    """

    prim_entries = []
    add_entries = []
    authors = []
    outlist = []
    dups = []

    for record in record_list:
        author = record.find('.//*[@tag="100"]/*[@code="a"]').text

        # prüfen ob MARC 700 vorhanden
        if record.find('.//*[@tag="700"]/*[@code="a"]') is not None:
            contr = record.find('.//*[@tag="700"]/*[@code="a"]').text
        else:
            contr = None

        # sortieren
        if contr in authors:
            prim_entries.append(author)
            add_entries.append(contr)
            dups.append(record)
        else:
            outlist.append(record)
            authors.append(author)


    for entry in prim_entries:
        if entry not in add_entries:
            print("700, no match: ", entry)

    return outlist


def check_type(record):
    """Akzeptiert einen Datensatz als Argument (xml.etree.ElementTree.Element)
    und checkt, zu welchem Typ Hochschulschrift es gehört. Gibt je nach Typ
    einen String zurück.
    """
    if record.find('./*[@tag="971"][@ind1="7"]/*[@code="i"]', ns) is not None:
        return "Elektronisch nicht zugänglich"
    elif record.find('./*[@tag="971"][@ind1="7"]/*[@code="a"]', ns) is not None:
        return "Gesperrt"
    else:
        return "elektronisch zugänglich"

def alloc_to_tree(record_list):
    """Ordnet jeden record dem jeweiligen xml-Baum zu. Akzeptiert eine Liste
    von record-Elementen als Argument
    """
    for record in record_list:
        hss_type = check_type(record)
        if hss_type == "Elektronisch nicht zugänglich":
            el_nicht.append(record)
        elif hss_type == "Gesperrt":
            gesperrt.append(record)
        else:
            el_zug.append(record)

def write_tree(tree, outfile):
    """Schreibt "tree" in die Datei "outfile". Akzeptiert ein tree-Objekt und einen
    String (Dateiname für die Ausgabedatei)
    """
    filename = outfile + "_{:%Y-%m-%d_%H-%M}.xml".format(datetime.datetime.now()) 
    tree = ET.ElementTree(tree)
    tree.write(filename, encoding="utf-8", xml_declaration=True)

def main():
    # Verarbeitung
    records = read_input_files("input")
    alloc_to_tree(records)
    write_tree(el_zug, "el_zug")
    write_tree(el_nicht, "el_nicht")
    write_tree(gesperrt, "gesperrt")
