from subprocess import call
import filecmp
import sys
import tempfile


simple_sch = "blink1_v1a.sch"
simple_sch_csv = "blink1_v1a_sch.csv"

simple_brd = "blink1_v1a.brd"
simple_brd_csv = "blink1_v1a_brd.csv"
simple_brd_pdf = "blink1_v1a_brd.pdf"

def get_formatted_content(pdf_content):
    cmd = 'pdftocairo -pdf - -' # you can replace "pdftocairo -pdf" with "pdftotext" if you want to get diff info
    ps = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = ps.communicate(input=pdf_content)
    if ps.returncode != 0:
        raise OSError(ps.returncode, cmd, stderr)
    return stdout

def test_sticker_bom():
    try:
        temp = tempfile.NamedTemporaryFile()
        try:
            print (temp.name)
            retcode = call("python eagle-bom.py" + " --in=test/files/" + simple_brd + " --out="+temp.name+" -t sticker", shell=True)
            assert retcode == 0
        except OSError as e:
            assert 0

        c1 = get_formatted_content(open('test/files'+simple_brd_pdf).read())
        c2 = get_formatted_content(open('/tmp/sticker.pdf').read())
        assert cmp(c1, c2)
    finally:
        temp.close()
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
        retcode = call("python eagle-bom.py --foobar", shell=True)
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

