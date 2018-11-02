from ..hss import *

def test_read_input_files():
    indir_small = "tests/testdata/input"
    small_list = read_input_files(indir_small)
    assert len(small_list) == 8
    assert type(small_list[0]) == pymarc.Record

def test_get_institution_dict():
    d = get_institution_dict()
    assert type(d) == dict
    assert len(d) > 0

def test_get_inst_code():
    d = get_institution_dict()
    assert get_inst_code(d, "UNI for LIFE") == ("UNI for LIFE", "ioo:UG:UL")
    assert get_inst_code(d,"NN") == (None, None)
    assert get_inst_code(d, "Institut für Dogmatik") == ("Katholisch-Theologische Fakultät", "ioo:UG:KT:DO")

def test_check_type():
    reclist = read_input_files("tests/testdata/input")

    assert check_type(reclist[0]) == "Elektronisch zugänglich"
    assert check_type(reclist[1]) == "Gesperrt"
    assert check_type(reclist[2]) == "Elektronisch zugänglich"
    assert check_type(reclist[3]) == "Elektronisch zugänglich"
    assert check_type(reclist[4]) == "Gesperrt"
    assert check_type(reclist[5]) == "Elektronisch nicht zugänglich"

def test_dedup():
    pass

def test_process_record():
    pass
