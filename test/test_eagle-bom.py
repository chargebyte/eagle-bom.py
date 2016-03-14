from subprocess import call
import filecmp
import sys

simple_sch = "blink1_v1a.sch"
simple_sch_csv = "blink1_v1a_sch.csv"

simple_brd = "blink1_v1a.brd"
simple_brd_csv = "blink1_v1a_brd.csv"

def test_sticker_bom():
    try:
        retcode = call("python eagle-bom.py" + " --in=test/files/" + simple_brd + " --out=/tmp/sticker.pdf -t sticker", shell=True)
        assert retcode == 0
    except OSError as e:
        assert 0

    #assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_brd_csv) 
    

def test_value_bom(): 
    #test brd > bom way
    try:
        retcode = call("python eagle-bom.py" + " --in=test/files/" + simple_brd + " --out=/tmp/simple.csv", shell=True)
        assert retcode == 0
    except OSError as e:
        assert 0

    assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_brd_csv) 

    #test sch > bom way
    try:
        retcode = call("python eagle-bom.py" + " --in=test/files/" + simple_sch + " --out=/tmp/simple.csv", shell=True)
        assert retcode == 0
    except OSError as e:
        assert 0

    assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_sch_csv) 
    

def test_cli_errors():
    try:
        #call script with garbage parameters
        retcode = call("python eagle-bom.py --foobar >/tmp/stderr", shell=True)
        assert retcode == 2	
        #try to pass an invalid output type
        retcode = call("python eagle-bom.py" + " --in=test/files/" + simple_brd + " --out=/tmp/simple.csv -t foobar", shell=True)
        assert retcode == 5
    except OSError as e:
        assert 0

def test_cli_stdin():
    try:
        #call script by passing brd via stdin
        retcode = call("cat test/files/" + simple_brd + "|python eagle-bom.py --out=/tmp/simple.csv", shell=True)
        assert retcode == 0
        assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_brd_csv) 

        #call script by passing sch via stdin
        retcode = call("cat test/files/" + simple_sch + "|python eagle-bom.py --out=/tmp/simple.csv", shell=True)
        assert retcode == 0
        assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_sch_csv) 

    except OSError as e:
        assert 0

def test_cli_stdout():
    try:
        #call script and return CSV via stdout
        retcode = call("python eagle-bom.py --in=test/files/" + simple_brd + ">/tmp/simple.csv", shell=True)
        assert retcode == 0
        assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_brd_csv) 

        #call script by passing sch via stdin
        retcode = call("python eagle-bom.py --in=test/files/" + simple_sch + ">/tmp/simple.csv", shell=True)
        assert retcode == 0
        assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_sch_csv) 

    except OSError as e:
        assert 0


def test_cli_stdin_stdout():
    try:
        #call script and return CSV via stdout
        retcode = call("cat test/files/" + simple_brd + "|python eagle-bom.py>/tmp/simple.csv", shell=True)
        assert retcode == 0
        assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_brd_csv) 

        #call script by passing sch via stdin
        retcode = call("cat test/files/" + simple_sch + "|python eagle-bom.py>/tmp/simple.csv", shell=True)
        assert retcode == 0
        assert filecmp.cmp('/tmp/simple.csv', 'test/files/'+simple_sch_csv) 

    except OSError as e:
        assert 0

