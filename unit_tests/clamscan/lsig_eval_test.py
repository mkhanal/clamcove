# Copyright (C) 2026 Cisco Systems, Inc. and/or its affiliates. All rights reserved.

"""
Run clamscan tests of which logical signatures are evaluated.

Logical signatures are evaluated sparsely: only the ones a subsignature matched
and the ones that can hold with no subsignature matched. Each test scans the
same files under every CL_LSIG_EVAL mode and asserts the exact alerts, so a
logical signature that sparse evaluation wrongly skips fails the test.
"""

import collections
import os
import sys
from zipfile import ZIP_STORED, ZipFile

sys.path.append('../unit_tests')
import testcase

NEVER = '4e455645525345454e515151'  # NEVERSEENQQQ, in none of the test files
MARKER = '4d41524b455241414141'  # MARKERAAAA
OTHER = '5a5a5a595959585858'  # ZZZYYYXXX, in none of the test files
TARGET = 'Engine:81-255,Target:0'

FILES = {
    'plain.txt': b'just some text without anything interesting in it at all......',
    'size150.txt': b'x' * 150,
    'marker_small.txt': b'MARKERAAAA hello',
    'marker3.txt': b'MARKERAAAA MARKERAAAA MARKERAAAA tail',
    'pcre.txt': b'PCRETRIG abc123xyz',
    'pcre_no_match.txt': b'PCRETRIG abc12xyz',
    'pcre_no_trigger.txt': b'abc123xyz only',
    'pcre_zero_trigger.txt': b'qwe123rty and nothing else',
    'bcomp41.txt': b'BCOMPHDR41 rest',
    'bcomp42.txt': b'BCOMPHDR42 rest',
    'macro_ok.txt': b'xxMACROHEADabcMACROTAILyyMACROHEADzz',
    'macro_far.txt': b'xxMACROHEADabcdefghijklmnopqrstuvwxyz0123MACROTAILyyMACROHEADzz',
    'mixed.txt': b'MARKERAAAA PCRETRIG abc123xyz BCOMPHDR42',
}

MODES = [None, 'sparse', 'full', 'verify']


def ldb(*lines):
    return '\n'.join(line.format(t=TARGET, never=NEVER, marker=MARKER, other=OTHER) for line in lines) + '\n'


class TC(testcase.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TC, cls).setUpClass()

        TC.path_files = TC.path_tmp / 'lsig-eval-files'
        TC.path_files.mkdir(parents=True)
        for name, content in FILES.items():
            (TC.path_files / name).write_bytes(content)

        with ZipFile(TC.path_files / 'inner.zip', 'w', ZIP_STORED) as zf:
            zf.writestr('marker_small.txt', FILES['marker_small.txt'])
            zf.writestr('plain.txt', FILES['plain.txt'])
        with ZipFile(TC.path_files / 'outer.zip', 'w', ZIP_STORED) as zf:
            zf.write(TC.path_files / 'inner.zip', 'inner.zip')
            zf.writestr('mixed.txt', FILES['mixed.txt'])

    @classmethod
    def tearDownClass(cls):
        super(TC, cls).tearDownClass()

    def setUp(self):
        super(TC, self).setUp()

    def tearDown(self):
        super(TC, self).tearDown()
        self.verify_valgrind_log()

    def make_db(self, **files):
        """Write the database files (extension=content) into a new directory and return it."""
        path_db = TC.path_tmp / 'lsig-eval-db-{}'.format(len(list(TC.path_tmp.glob('lsig-eval-db-*'))))
        path_db.mkdir()
        for extension, content in files.items():
            (path_db / 'lsig-eval.{}'.format(extension)).write_text(content)
        return path_db

    def scan(self, path_db, names, mode, options=''):
        """Scan the named files and return {file name: Counter of alert names}."""
        command = '{valgrind} {valgrind_args} {clamscan} -d {path_db} {options} {files}'.format(
            valgrind=TC.valgrind, valgrind_args=TC.valgrind_args, clamscan=TC.clamscan,
            path_db=path_db, options=options,
            files=' '.join(str(TC.path_files / name) for name in names),
        )

        saved = os.environ.pop('CL_LSIG_EVAL', None)
        if mode is not None:
            os.environ['CL_LSIG_EVAL'] = mode
        try:
            output = self.execute_command(command)
        finally:
            os.environ.pop('CL_LSIG_EVAL', None)
            if saved is not None:
                os.environ['CL_LSIG_EVAL'] = saved

        alerts = {name: collections.Counter() for name in names}
        for line in output.out.splitlines():
            if not line.endswith(' FOUND'):
                continue
            path, _, alert = line[:-len(' FOUND')].rpartition(': ')
            alerts[os.path.basename(path)][alert.removesuffix('.UNOFFICIAL')] += 1

        assert output.ec == (1 if any(alerts.values()) else 0), 'CL_LSIG_EVAL={}: exit code {}: {}'.format(mode, output.ec, output.err)
        assert 'Sparse logical signature evaluation would skip' not in output.err, output.err
        return alerts

    def verify_alerts(self, path_db, expected, options='--allmatch'):
        """Scan the files of `expected` under every mode, compare the alert names of each, and require every mode to alert as often as the default."""
        names = list(expected)
        default = None
        for mode in MODES:
            actual = self.scan(path_db, names, mode, options)
            for name in names:
                assert set(actual[name]) == set(expected[name]), \
                    'CL_LSIG_EVAL={} {}: expected {}, got {}'.format(mode, name, sorted(set(expected[name])), sorted(actual[name]))
            if default is None:
                default = actual
            assert actual == default, \
                'CL_LSIG_EVAL={}: {} alerts, the default {}'.format(mode, actual, default)

    def test_logic_true_at_zero_counts(self):
        self.step_name('Test a logical signature whose logic holds with every subsignature count at zero')

        path_db = self.make_db(ldb=ldb(
            'Zero.Equal;{t};0=0;{never}',
            'Zero.Less;{t};0<1;{never}',
            'Zero.Group;{t};(0|1)=0;{never};{other}',
            'Zero.Or;{t};0|1=0;{never};{other}',
            'Zero.WithFileSize;{t},FileSize:100-200;0=0&1<1;{never};{other}',
            'Zero.MatchedAndNotMatched;{t};0&1=0;{marker};{never}',
        ))

        zero = ['Zero.Equal', 'Zero.Less', 'Zero.Group', 'Zero.Or']
        self.verify_alerts(path_db, {
            'plain.txt': zero,
            'size150.txt': zero + ['Zero.WithFileSize'],
            'marker_small.txt': zero + ['Zero.MatchedAndNotMatched'],
        })

    def test_logic_needing_a_match(self):
        self.step_name('Test a logical signature whose logic needs a subsignature count')

        path_db = self.make_db(ldb=ldb(
            'Count.AtLeastOne;{t};0;{marker}',
            'Count.MoreThanTwo;{t};0>2;{marker}',
            'Count.ExactlyThree;{t};0=3;{marker}',
            'Count.SmallFile;{t},FileSize:0-20;0;{marker}',
        ))

        self.verify_alerts(path_db, {
            'plain.txt': [],
            'marker_small.txt': ['Count.AtLeastOne', 'Count.SmallFile'],
            'marker3.txt': ['Count.AtLeastOne', 'Count.MoreThanTwo', 'Count.ExactlyThree'],
            'mixed.txt': ['Count.AtLeastOne'],
        })

    def test_macro_subsignature(self):
        self.step_name('Test a logical signature with a macro subsignature')

        path_db = self.make_db(
            ldb=ldb(
                'Macro.Matched;{t};0&1;4d4143524f48454144;${{0-20}}7$',
                'Macro.NotMatched;{t};0&1=0;4d4143524f48454144;${{0-20}}7$',
            ),
            ndb='Macro.Group:0:$7:4d4143524f5441494c\n',
        )

        self.verify_alerts(path_db, {
            'plain.txt': [],
            'macro_ok.txt': ['Macro.Matched'],
            'macro_far.txt': ['Macro.NotMatched'],
        })

    def test_byte_compare_subsignature(self):
        self.step_name('Test a logical signature with a byte-compare subsignature')

        path_db = self.make_db(ldb=ldb(
            'ByteCompare.Matched;{t};1;42434f4d50484452;0(>>8#de2#=42)',
            'ByteCompare.NotMatched;{t};0&1=0;42434f4d50484452;0(>>8#de2#=42)',
        ))

        self.verify_alerts(path_db, {
            'plain.txt': [],
            'bcomp41.txt': ['ByteCompare.NotMatched'],
            'bcomp42.txt': ['ByteCompare.Matched'],
            'mixed.txt': ['ByteCompare.Matched'],
        })

    def test_pcre_subsignature(self):
        self.step_name('Test a logical signature with a PCRE subsignature, also one triggered by 0=0')

        path_db = self.make_db(ldb=ldb(
            'Pcre.Triggered;{t};1;5043524554524947;0/abc[0-9]{{3}}xyz/',
            'Pcre.ZeroTrigger;{t};1;{never};0=0/qwe[0-9]{{3}}rty/',
        ))

        self.verify_alerts(path_db, {
            'plain.txt': [],
            'pcre.txt': ['Pcre.Triggered'],
            'pcre_no_match.txt': [],
            'pcre_no_trigger.txt': [],
            'pcre_zero_trigger.txt': ['Pcre.ZeroTrigger'],
            'mixed.txt': ['Pcre.Triggered'],
        })

    def test_yara_rules(self):
        self.step_name('Test YARA rules whose condition holds with no string matched')

        path_db = self.make_db(yar='\n'.join([
            'rule Yara_NotString { strings: $a = "NEVERSEENQQQ" condition: not $a }',
            'rule Yara_CountZero { strings: $a = "NEVERSEENQQQ" condition: #a == 0 }',
            'rule Yara_String { strings: $a = "MARKERAAAA" condition: $a }',
            'rule Yara_TwoStrings { strings: $a = "MARKERAAAA" $b = "PCRETRIG" condition: $a and $b }',
            'rule Yara_AtStart { strings: $a = "MARKERAAAA" condition: $a at 0 }',
        ]) + '\n')

        absent = ['YARA.Yara_NotString', 'YARA.Yara_CountZero']
        marker = ['YARA.Yara_String', 'YARA.Yara_AtStart']
        self.verify_alerts(path_db, {
            'plain.txt': absent,
            'marker_small.txt': absent + marker,
            'marker3.txt': absent + marker,
            'mixed.txt': absent + marker + ['YARA.Yara_TwoStrings'],
        })

    def test_pua_signatures(self):
        self.step_name('Test a PUA logical signature with and without --detect-pua')

        path_db = self.make_db(
            ldb=ldb('Pua.Control;{t};0;{marker}'),
            ldu=ldb(
                'PUA.Pua.Zero;{t};0=0;{never}',
                'PUA.Pua.Marker;{t};0;{marker}',
            ),
        )

        self.verify_alerts(path_db, {
            'plain.txt': [],
            'marker_small.txt': ['Pua.Control'],
        })
        self.verify_alerts(path_db, {
            'plain.txt': ['PUA.Pua.Zero'],
            'marker_small.txt': ['Pua.Control', 'PUA.Pua.Zero', 'PUA.Pua.Marker'],
        }, options='--allmatch --detect-pua')

    def test_zip_in_zip(self):
        self.step_name('Test logical signatures with a container constraint on a zip inside a zip')

        path_db = self.make_db(ldb=ldb(
            'Zip.Zero;{t};0=0;{never}',
            'Zip.ZeroInZip;{t},Container:CL_TYPE_ZIP;0=0;{never}',
            'Zip.ZeroInZipInZip;{t},Intermediates:CL_TYPE_ZIP>CL_TYPE_ZIP;0=0;{never}',
            'Zip.MarkerInZip;{t},Container:CL_TYPE_ZIP;0;{marker}',
        ))

        self.verify_alerts(path_db, {
            'inner.zip': ['Zip.Zero', 'Zip.ZeroInZip', 'Zip.MarkerInZip'],
            'outer.zip': ['Zip.Zero', 'Zip.ZeroInZip', 'Zip.ZeroInZipInZip', 'Zip.MarkerInZip'],
        })

    def test_all_match(self):
        self.step_name('Test that every matching signature of every kind alerts in all-match mode')

        path_db = self.make_db(
            ldb=ldb(
                'All.Zero;{t};0=0;{never}',
                'All.Marker;{t};0;{marker}',
                'All.MarkerNoOther;{t};0&1=0;{marker};{other}',
            ),
            ndb='All.Ndb:0:*:' + MARKER + '\n',
            yar='rule All_Yara { strings: $a = "MARKERAAAA" condition: $a }\n',
        )

        self.verify_alerts(path_db, {
            'plain.txt': ['All.Zero'],
            'marker_small.txt': ['All.Zero', 'All.Marker', 'All.MarkerNoOther', 'All.Ndb', 'YARA.All_Yara'],
        })

    def test_first_match(self):
        self.step_name('Test that the first signature in order alerts in first-match mode')

        touched_first = self.make_db(ldb=ldb(
            'First.Touched;{t};0;{marker}',
            'First.Zero;{t};0=0;{never}',
        ))
        self.verify_alerts(touched_first, {
            'plain.txt': ['First.Zero'],
            'marker_small.txt': ['First.Touched'],
        }, options='')

        zero_first = self.make_db(ldb=ldb(
            'First.Zero;{t};0=0;{never}',
            'First.Touched;{t};0;{marker}',
        ))
        self.verify_alerts(zero_first, {
            'plain.txt': ['First.Zero'],
            'marker_small.txt': ['First.Zero'],
        }, options='')
