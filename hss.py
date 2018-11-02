#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import pymarc
import os
import datetime
# import texttable as TT
from sys import argv
import requests
from calendar import monthrange

if len(argv) == 1:
    machine = "w"
else:
    machine = argv[1]

def get_institution_dict():
    """Return a dictionary of inst_strs and inst_codes."""

    inst_dict = {}
    vl_mets = requests.get(
        "http://unipub.uni-graz.at/UGR/mets/classification/id/110856")
    tree = ET.fromstring(vl_mets.text)

    fakultaeten = tree.findall(
        './/*[@LABEL="Fakultäten der Universität Graz"]/*')

    # das dict befüllen
    for fakultaet in fakultaeten:
        fak_label = fakultaet.attrib['LABEL']
        # die einzelnen Institute einfüllen
        for inst in fakultaet:
            inst_label = inst.attrib['LABEL']
            inst_id = inst.attrib["ID"]
            if not inst_id == "Externe Institute":
                inst_dict[inst_label] = (fak_label, inst_id)
            else:
                continue

    return inst_dict

def get_inst_code(code_dict, institut):
    """Return the code for a given (fakultät, inst)-tuple of strings."""
    if institut == "UNI for LIFE":
        return ("UNI for LIFE", "ioo:UG:UL")
    elif institut in code_dict.keys():
        return code_dict[institut]
    else:
        return None, None

def read_input_files(indir):
    """Liest alle Input-Files und gibt eine Liste mit record-Objekten (eines pro
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

    # die einzelen Datensätze zur Liste records hinzufügen
    for infile in infiles:
        with open(infile) as fh:
            reader = pymarc.parse_xml_to_array(fh)
            for rec in reader:
                records.append(rec)

    return records

def check_type(record):
    """Akzeptiert einen Datensatz als Argument (xml.etree.ElementTree.Element)
    und checkt, zu welchem Typ Hochschulschrift es gehört. Gibt je nach Typ
    einen String zurück.
    """

    hss_type = None
    for f in record.get_fields("971"):
        if not f.indicators[0] == "7":
            continue
        else:
            if "Arbeit gesperrt" in f.value():
                hss_type = "Gesperrt"
            elif "AutorIn stimmte der Freigabe des elektronischen Dokuments nicht zu" in f.value():
                hss_type = "Elektronisch nicht zugänglich"

    if hss_type == None:
        return "Elektronisch zugänglich"
    else:
        return hss_type


# TODO
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


# DONE
def process_record(record):
    """Verarbeitet einen Datensatz."""

    # Unabhängig vom Typ zu machen
    # DONE Institutsionscodes
    for field in record.get_fields("971"):
        if not field.indicators[0] == "5":
            continue
        else:
            inst_field = field

    if inst_field["b"] == "UNI for LIFE":
        institut = "UNI for LIFE"
    else:
        institut = inst_field["c"]

    fakultaet, inst_code = get_inst_code(inst_dict, institut)

    if inst_code is None:
        bad_code.append(institut)
    elif inst_code == "ioo:UG:UL":
        inst_field["0"] = inst_code
        inst_field.delete_subfield("c")
    else:
        inst_field["0"] = inst_code
        inst_field["b"] = fakultaet

    # DONE 005 erstellen
    record.add_ordered_field(
        pymarc.Field(
            tag = "005"
        ))
    record["005"].data = datetime.datetime.now().strftime("%Y%m%d%H%M%S.0")
    # DONE Datum in 008
    record["008"].data = datetime.datetime.now().strftime("%y%m%d") + record["008"].data[6:]
    # DONE Wickelfelder entfernen
    for field in record.get_fields("974"):
        record.remove_field(field)
    # DONE in 040 UBG durch AT-UBG ersetzen
    record["040"]["a"] = "AT-UBG"

    # Änderungen je nach HSS-Typ
    # record type checken, um entsprechende Verarbeitung machen zu können
    rec_type = check_type(record)
    if not rec_type == "Elektronisch zugänglich":
        # DONE "UBG-HS-Online" in 040 ## $$c schreiben
        record["040"]["c"] = "UBG-HS-Online"
        # DONE Feld für Inventar erstellen
        inv_field = pymarc.Field(
            tag = "995",
            indicators = [" ", " "],
            subfields = [])
        record.add_ordered_field(inv_field)
        # DONE Basekennung auslesen (für Exemplarstatistik)
        basekennung = record["970"]["d"]
        if basekennung == "HS-DISS":
            stat = "DISS"
        else:
            stat = "DIPL"
        # DONE je nach rectype die verschiedenen Subfelder checken
        if rec_type == "Elektronisch nicht zugänglich":
            inv_field.subfields = ["p", "87",
                                   "b", "BHB",
                                   "c", "MAG",
                                   "s", stat,
                                   "9", "LOCAL"]
        elif rec_type == "Gesperrt":
            # Monatsletzten des Sperrdatums errechnen
            for field in record.get_fields("971"):
                if not field.indicators[0] == "7":
                    continue
                else:
                    sperrfeld = field
            sperrjahr, sperrmonat = field["c"].split("-")
            sperrtag = str(monthrange(int(sperrjahr), int(sperrmonat))[1]).zfill(2)
            sperrdatum = "-".join([sperrjahr, sperrmonat, sperrtag])
            public_note = f"Arbeit gesperrt bis {sperrdatum}"
            sperrfeld["c"] = sperrdatum
            # alles in inventarfeld schreiben
            inv_field.subfields = ["p", "30",
                                   "b", "BHB",
                                   "c", "GDISS",
                                   "s", stat,
                                   "n", public_note,
                                   "9", "LOCAL"]



# DONE
def write_loadfile(record_list, out_dir):
    """Schreibt "tree" in die Datei "outfile". Akzeptiert ein tree-Objekt und einen
    String (Dateiname für die Ausgabedatei)
    """
    filename = os.path.join(
        out_dir, "loadfile" + "_{:%Y-%m-%d_%H-%M}.xml".format(datetime.datetime.now()))
    writer = pymarc.XMLWriter(open(filename, "wb"))
    for record in record_list:
        writer.write(record)
    writer.close()

def move_files_to_arch(stage, arch):
    """Verschiebt die Dateien von stage nach arch."""
    # Liste der Input-Dateien erstellen
    files = []
    for filename in os.listdir(stage):
        files.append(
            (os.path.join(stage, filename), os.path.join(arch, filename)))

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
        rep_dir = "reports"
        arch = "arch"
        loadfiles = "loadfiles"

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

inst_dict = get_institution_dict()
bad_code = []
def testit():
    outdir = "tests/loadfiles"
    l = read_input_files("tests/testdata/input")

    for rec in l:
        process_record(rec)

    write_loadfile(l, outdir)
