#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import os
import datetime
import texttable as TT
from sys import argv
import requests
from calendar import monthrange

if len (argv) == 1:
    machine = "w"
else:
    machine = argv[1]

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

# Liste für die Institutscodes, die nicht in VL definiert sind
bad_code = []

def get_institution_dict():
    """Return a dictionary of inst_strs and inst_codes."""

    inst_dict = {}
    vl_mets = requests.get("http://unipub.uni-graz.at/UGR/mets/classification/id/110856")
    tree = ET.fromstring(vl_mets.text)

    fakultaeten = tree.findall('.//*[@LABEL="Fakultäten der Universität Graz"]/*')

    # das dict befüllen
    for fakultaet in fakultaeten:
        fak_label = fakultaet.attrib['LABEL']
        # die einzelnen Institute einfüllen
        for inst in fakultaet:
            inst_label = inst.attrib['LABEL']
            inst_id = inst.attrib["ID"]
            inst_dict[(fak_label, inst_label)] = inst_id

    return inst_dict

# TODO als lokale Variable implementieren
inst_dict = get_institution_dict()
def get_inst_code(code_dict, inst_strs):
    """Return the code for a given (fakultät, inst)-tuple of strings."""
    if inst_strs[0] == "UNI for LIFE":
        return "ioo:UG:UL"
    elif inst_strs in code_dict.keys():
        return code_dict[inst_strs]
    else:
        return None

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
        if filename.startswith("."):
            continue
        else:
            infiles.append(os.path.join(input_dir, filename))

    # die einzelen Datensätze deduplizieren und zur Liste records hinzufügen
    for file in infiles:
        tree = ET.parse(file)
        root = tree.getroot()
        for record in root.findall("./marc:record", ns):
            records.append(record)

    return records

def print_names(record_list):
    """Helper function die für jeden Datensatz in einer Liste den Inhalt von
    Feld 100 $$a ausgibt"""
    for record in record_list:
        print(record.find(make_xpath("100","**","a")).text)

def dedup(record_list):
    """Entfernt dublette Datensätze, die dadurch entstehen, dass mehrere
    Personen gemeinsam eine Arbeit verfassen. Nimmt eine Liste von
    record-Elementen als Input und gibt eine deduplizierte Liste zurück.
    """

    field_100 = make_xpath("100", "**", "a")
    field_700 = make_xpath("700", "**", "a")

    authors = []
    outlist = []
    dups = []

    for record in record_list:
        author = record.find('.//*[@tag="100"]/*[@code="a"]').text

        # prüfen ob MARC 700 vorhanden
        if record.find(field_700) is None:
            authors.append(author)
            outlist.append(record)
            continue
        else:
            people = []
            people.append(author)
            for p in record.findall(field_700):
                people.append(p.text)

            dup = False
            for p in people:
                if p in authors:
                    dup = True
                else:
                    authors.append(p)

            if dup == False:
                outlist.append(record)
            else:
                dups.append(record)


    return outlist, dups


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
        return "Elektronisch zugänglich"

def make_tree(record_list):
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

def inventory(record_list):
    """Fügt das Feld für den physischen Bestand hinzu"""
    field970_sfd = make_xpath("970", "2 ", "d")
    sperre_ende = make_xpath("971", "7 ", "c")

    for record in record_list:
    # Instituscode für VL
        fakultaet = record.find(make_xpath("971", "5 ", "b")).text
        institut = record.find(make_xpath("971", "5 ", "c")).text
        inst_element = record.find(make_xpath("971", "5 ", "c"))
        inst_code = get_inst_code(inst_dict, (fakultaet, institut))

        if inst_code is None:
            bad_code.append((fakultaet, institut))
        elif inst_code == "ioo:UG:UL":
            record.find(make_xpath("971", "5 ", "0")).text = inst_code
            record.find(make_xpath("971", "5 ", "c")).text = ""
        else:
            record.find(make_xpath("971", "5 ", "0")).text = inst_code


        rec_type = check_type(record)

        # generate 005 field
        field005 = ET.Element("marc:controlfield", attrib={"tag": "005"})
        field005.text = datetime.datetime.now().strftime("%Y%m%d%H%M%S.0")
        record.append(field005)

        # Datum in 008/00-05 schreiben
        field008 = record.find('./*[@tag="008"]')
        field008.text = datetime.datetime.now().strftime("%y%m%d") + field008.text[6:]

        # Entfernt die Wickelfelder
        for wf in record.findall('./*[@tag="974"]', ns):
            record.remove(wf)

        # In 040 "UBG" durch "AT-UBG" ersetzen
        record.find(make_xpath("040", "**", "a")).text = "AT-UBG"

        if rec_type == "Elektronisch zugänglich":
            # kein inventar für elektronisch zugängliche Arbeiten
            continue
        else:
            # Feld für Inventar einfügen

            # Zuerst das Feld mit den Subfeldern vorbereiten
            field995 = ET.Element("marc:datafield", attrib={'tag': '995', 'ind1': ' ', 'ind2': " "})
            f995_sfp = ET.Element("marc:subfield", attrib={'code': "p"})
            f995_sfb = ET.Element("marc:subfield", attrib={'code': "b"})
            f995_sfc = ET.Element("marc:subfield", attrib={'code': "c"})
            f995_sfs = ET.Element("marc:subfield", attrib={'code': "s"})
            f995_sfn = ET.Element("marc:subfield", attrib={'code': "n"})
            f995_sf9 = ET.Element("marc:subfield", attrib={'code': "9"})
            field995.append(f995_sfp)
            field995.append(f995_sfb)
            field995.append(f995_sfc)
            field995.append(f995_sfs)
            field995.append(f995_sfn)
            field995.append(f995_sf9)

            # 040 $$c auf UBG-HS-online stellen
            record.find(make_xpath("040", "**", "c")).text = "UBG-HS-online"

            # checken welche Statistik passt
            basekennung = record.find(field970_sfd).text
            if basekennung == "HS-DISS":
                stats = "DISS"
            else:
                stats = "DIPL"

            # je nach Typ Bestand hinzufügen
            f995_sf9.text = "LOCAL"
            if rec_type == "Elektronisch nicht zugänglich":
                f995_sfp.text = "87"
                f995_sfb.text = "BHB"
                f995_sfc.text = "MAG"
                f995_sfs.text = stats
            elif rec_type == "Gesperrt":
                f995_sfp.text = "30"
                f995_sfb.text = "BHB"
                f995_sfc.text = "GDISS"
                f995_sfs.text = stats
                sperrjahr, sperrmonat = record.find(sperre_ende).text.split("-")
                sperrtag = str(monthrange(int(sperrjahr), int(sperrmonat))[1]).zfill(2)
                sperrdatum = "-".join([sperrjahr, sperrmonat, sperrtag])
                f995_sfn.text = f"Arbeit gesperrt bis {sperrdatum}"
                record.find(sperre_ende).text = sperrdatum
            else:
                continue


            record.append(field995)

    return record_list

def write_tree(record_list, out_dir):
    """Schreibt "tree" in die Datei "outfile". Akzeptiert ein tree-Objekt und einen
    String (Dateiname für die Ausgabedatei)
    """
    filename = os.path.join(out_dir, "loadfile" + "_{:%Y-%m-%d_%H-%M}.xml".format(datetime.datetime.now())) 
    output = ET.fromstring(template)
    for record in record_list:
        output.append(record)

    tree = ET.ElementTree(output)
    tree.write(filename, encoding="utf-8", xml_declaration=True)

def write_report(record_list, flag, report_dir=""):
    xp_name = make_xpath("100", "**", "a")
    xp_title = make_xpath("245", "**", "a")
    # header, je nach report
    if flag == "loadfile":
        filename = os.path.join(report_dir, "{:%Y-%m-%d_%H-%M}".format(datetime.datetime.now()) + "_report-loadfile.txt" )
        header = " " * 27 + "*** Zu ladende Datensätze {:%Y-%m-%d %H:%M} ***\n".format(datetime.datetime.now())  + " " * 27 + "=" * 51 + "\n\n"
    elif flag == "duplicates":
        filename = os.path.join(report_dir, "{:%Y-%m-%d_%H-%M}".format(datetime.datetime.now()) + "_report_duplicates.txt")
        header = " " * 27 + "*** Nicht zu ladende Duplikate {:%Y-%m-%d %H:%M} ***\n".format(datetime.datetime.now())  + " " * 27 + "=" * 51 + "\n\n"
    else:
        header = ""

    table = TT.Texttable()
    table.header(["VerfasserIn", "Titel", "Art der Hochschulschrift"])
    table.set_deco(table.HEADER)
    table.set_cols_width([25, 50, 25])
    for record in record_list:
        name = record.find(xp_name).text
        title = record.find(xp_title).text
        hss_type = check_type(record)
        table.add_row([name, title, hss_type])

    tbl_str = table.draw()

    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(header)
        fh.write(tbl_str)

def move_files_to_arch(stage, arch):
    """Verschiebt die Dateien von stage nach arch."""
    # Liste der Input-Dateien erstellen
    files = []
    for filename in os.listdir(stage):
        files.append((os.path.join(stage, filename), os.path.join(arch, filename)))

    for fromfile, tofile in files:
        os.rename(fromfile, tofile)


def main():
    # Pfade
    # Pfade für PROD
    if machine == "w":
        # Ausführung unter Windows
        stage = "y:/HOCHSCHULSCHRIFTEN/Alma/stage"
        rep_dir = "y:/HOCHSCHULSCHRIFTEN/Alma/Reports"
        arch = "y:/HOCHSCHULSCHRIFTEN/Alma/MRC-Archiv"
        loadfiles = "y:/HOCHSCHULSCHRIFTEN/Alma/loadfiles"
    elif machine == "l":
        # Pfade für Ausführung unter Linux
        stage = "/home/schuhs/Y/HOCHSCHULSCHRIFTEN/Alma/stage/"
        rep_dir = "/home/schuhs/Y/HOCHSCHULSCHRIFTEN/Alma/Reports"
        arch = "/home/schuhs/Y/HOCHSCHULSCHRIFTEN/Alma/MRC-Archiv"
        loadfiles = "/home/schuhs/Y/HOCHSCHULSCHRIFTEN/Alma/loadfiles"
    elif machine == "t":
        # Pfade für Tests relativ
        stage = "input"
        rep_dir =  "reports"
        arch =  "arch"
        loadfiles =  "loadfiles"

    # Pfade für Tests Windows
    # stage = "C:/Users/schuhs/projects/hss/input"
    # rep_dir =  "C:/Users/schuhs/projects/hss/reports"
    # arch =  "C:/Users/schuhs/projects/hss/arch"
    # loadfiles =  "c:/Users/schuhs/projects/hss/loadfiles"


    # Verarbeitung
    records, dups = dedup(read_input_files(stage))
    write_tree(inventory(records), loadfiles)
    write_report(records, "loadfile", rep_dir)
    write_report(dups, "duplicates", rep_dir)
    # move_files_to_arch(stage, arch)

    if len(bad_code) > 0:
        with open(rep_dir + "/bad_codes.txt", "w") as fh:
            fh.write("Codes, die in VL nicht vorhanden sind:\n")
            for code in bad_code:
                fh.write("\n" + str(code))
main()
