# encoding: utf-8

import os
import os.path
import sys
import time
import md5
import random

from jnius import autoclass


JRExporterParameter = autoclass('net.sf.jasperreports.engine.JRExporterParameter')
JasperExportManager = autoclass('net.sf.jasperreports.engine.JasperExportManager')
JasperFillManager = autoclass('net.sf.jasperreports.engine.JasperFillManager')
JRXmlDataSource = autoclass('net.sf.jasperreports.engine.data.JRXmlDataSource')
JRCsvExporter = autoclass('net.sf.jasperreports.engine.export.JRCsvExporter')
JRRtfExporter = autoclass('net.sf.jasperreports.engine.export.JRRtfExporter')
JRHtmlExporter = autoclass('net.sf.jasperreports.engine.export.JRHtmlExporter')
JRTextExporter = autoclass('net.sf.jasperreports.engine.export.JRTextExporter')
JRTextExporterParameter = autoclass('net.sf.jasperreports.engine.export.JRTextExporterParameter')
JRXlsExporter = autoclass('net.sf.jasperreports.engine.export.JRXlsExporter')
JasperCompileManager = autoclass('net.sf.jasperreports.engine.JasperCompileManager')

TMPDIR = '/tmp/pyJasper'

__revision__ = '$Revision$'


def ensure_dirs(dirlist):
    """Ensure that a dir and all it's parents exist."""
    for thedir in dirlist:
        if not os.path.exists(thedir):
            os.makedirs(thedir)
    

def gen_uuid():
    """Generates an hopfully unique ID."""
    return md5.new("%s-%f" % (time.time(), random.random())).hexdigest()
    

class JasperInterface:
    """This is the new style pyJasper Interface"""
    
    def __init__(self, designdatalist, xpath):
        """Constructor
        designdatalist: a dict {"template_var_name": "JRXML data"}.
        xpath:      The xpath expression passed to the report.
        """
        # depreciation check
        if isinstance(designdatalist, basestring):
            #warnings.warn("Passing the JRXML data as a string is deprecated. Use a dict of JRXML strings with template_var_name as key.", DeprecationWarning)
            # fix it anyway
            designdatalist = {'main': designdatalist}

        # Compile design if compiled version doesn't exist
        self.compiled_design = {}
        for design_name in designdatalist:
            self.compiled_design[design_name] = self._update_design(designdatalist[design_name])

        self.xpath = xpath
    
    def _update_design(self, designdata):
        """Compile the report design if needed."""
        designdata_hash = md5.new(designdata.encode('utf-8')).hexdigest()
        sourcepath = os.path.join(TMPDIR, 'reports')
        destinationpath = os.path.join(TMPDIR, 'compiled-reports')
        ensure_dirs([sourcepath, destinationpath])
        source_design = os.path.join(sourcepath, designdata_hash + '.jrxml')
        compiled_design = os.path.join(destinationpath, designdata_hash + '.jasper')
        
        if not os.path.exists(compiled_design):
            sys.stderr.write("generating report %s\n" % compiled_design)
            uuid = gen_uuid()
            fdesc = open(source_design, 'w')
            fdesc.write(designdata.encode('utf-8'))
            fdesc.close()
            JasperCompileManager.compileReportToFile(source_design, compiled_design + uuid)
            os.rename(compiled_design + uuid, compiled_design)

        return compiled_design
    
    def generate(self, xmldata, output_type='pdf'):
        """Generate Output with JasperReports."""
        start = time.time()
        xmlpath = os.path.join(TMPDIR, 'xml')
        outputpath = os.path.join(TMPDIR, 'output')
        oid = "%s-%s" % (md5.new(xmldata).hexdigest(), gen_uuid())
        ensure_dirs([xmlpath, outputpath])
        xmlfile = os.path.join(xmlpath, oid + '.xml')
        fdesc = open(xmlfile, 'w')
        fdesc.write(xmldata.encode('utf-8'))
        fdesc.close()
        
        output_filename = os.path.abspath(os.path.join(outputpath, oid + '.' + output_type))
        datasource = JRXmlDataSource(xmlfile, self.xpath)

        # convert to a java.util.Map so it can be passed as parameters
        map = JMap()
        for i in self.compiled_design:
            map[i] = self.compiled_design[i]

        # add the original xml document source so subreports can make a new datasource.
        map['XML_FILE'] = xmlfile

        jasper_print = JasperFillManager.fillReport(self.compiled_design['main'], map, datasource)

        if output_type == 'pdf':
            output_file = open(output_filename, 'wb')
            JasperExportManager.exportReportToPdfStream(jasper_print, output_file)
            output_file.close()
        elif output_type == 'xml':
            output_file = open(output_filename, 'w')
            JasperExportManager.exportReportToXmlStream(jasper_print, output_file)
            output_file.close()
        elif output_type == 'rtf':
            self.generate_rtf(jasper_print, output_filename)
        elif output_type == 'xls':
            self._generate_xls(jasper_print, output_filename)
        elif output_type == 'csv':
            self._generate_csv(jasper_print, output_filename)
        elif output_type == 'text':
            self._generate_text(jasper_print, output_filename)
        elif output_type == 'html':
            self._generate_html(jasper_print, output_filename)
        else:
            raise RuntimeError("Unknown output type %r" % (output_type))
        delta = time.time() - start
        sys.stderr.write('report %r generated in %.3f seconds\n' % (output_filename, delta))
        return open(output_filename, 'rb').read()
    
    def generate_rtf(self, jasper_print, output_filename):
        """Generate RTF output."""
        rtf_exporter = JRRtfExporter()
        rtf_exporter.setParameter(JRExporterParameter.JASPER_PRINT, jasper_print)
        rtf_exporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, output_filename)
        rtf_exporter.exportReport()

    def _generate_xls(self, jasper_print, output_filename):
        """Generate XLS output."""
        xls_exporter = JRXlsExporter()
        xls_exporter.setParameter(JRExporterParameter.JASPER_PRINT, jasper_print)
        xls_exporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, output_filename)
        xls_exporter.exportReport()

    def _generate_csv(self, jasper_print, output_filename):
        """Generate CSV output."""
        csv_exporter = JRCsvExporter()
        csv_exporter.setParameter(JRExporterParameter.JASPER_PRINT, jasper_print)
        csv_exporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, output_filename)
        csv_exporter.exportReport()

    def _generate_text(self, jasper_print, output_filename):
        """Generate Text output."""
        text_exporter = JRTextExporter()
        text_exporter.setParameter(JRExporterParameter.JASPER_PRINT, jasper_print)
        text_exporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, output_filename)
        text_exporter.setParameter(JRTextExporterParameter.PAGE_WIDTH, 80)
        text_exporter.setParameter(JRTextExporterParameter.PAGE_HEIGHT, 60)
        text_exporter.exportReport()

    def _generate_html(self, jasper_print, output_filename):
        """Generate HTML output."""
        html_exporter = JRHtmlExporter()
        html_exporter.setParameter(JRExporterParameter.JASPER_PRINT, jasper_print)
        html_exporter.setParameter(JRExporterParameter.OUTPUT_FILE_NAME, output_filename)
        html_exporter.exportReport()
    
