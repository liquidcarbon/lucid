# lucid/io.py

__doc__ = """
Input-Output (IO) functions for working with files and streams.
"""

#-----------------------------------------------------------------------------
# Logging
#-----------------------------------------------------------------------------
import logging
_l = logging.getLogger(__name__)


#-----------------------------------------------------------------------------
# Imports & Options
#-----------------------------------------------------------------------------

# External imports
from jinja2 import FileSystemLoader, PackageLoader, Environment, Template
from requests.models import Response
from subprocess import check_output
import os
import pandas as pd
import re

# Internal imports
from .util import MattrD, me, tnow


#-----------------------------------------------------------------------------
# Globals & Constants
#-----------------------------------------------------------------------------
IP = check_output(['hostname', '-i']).decode('utf-8')[:-1]
J2_FOLDER = os.path.abspath('j2/')
J2_DT_BASIC = 'dt_basic.j2.html'  # basic DataTables template

WEBCONF = MattrD({
    "title": "Cool Data",
    "active_page": "home",
    "template_file": "/path/to/file",
    "release_date": tnow(fmt='%Y-%b-%d %H:%M %Z'),
    "data": {
            "table_html": "<span>Insert table data</span>",
            "table_id": "sampledata",
            "table_class": "dt",
            "table_style": "padding: 4px 0px;",
            "sort_col": "1, \"asc\""
    }
})

HOMEDIR=os.environ['HOME']
WEBPORT = 8080
WEBSERVER = f'{IP}:{WEBPORT}/'
WEBTABLES_URL_JUPYTER = True  # display URL of published webtables in Jupyter
WWWFOLDER = f'{HOMEDIR}/www/'  # root folder of the webserver
if not os.path.exists(WWWFOLDER):
    os.mkdir(WWWFOLDER)

#-----------------------------------------------------------------------------
# Reading/Writing Excel
#-----------------------------------------------------------------------------

def _xlsheet(writer, df, sheet_name, **kwargs):
    """Saves DataFrame to a specified Excel sheet.

    Auxiliary function to xlsave.
    """

    df.to_excel(writer, sheet_name, **kwargs)
    #tweak column width
    for i in range(df.shape[1]):
        writer.sheets[sheet_name].set_column(i, i+1, len(df.columns[i]) + 4)


def xlsave(output_file, frames, sheets, **kwargs):
    """Saves one or more DataFrames to specified Excel sheet(s).

    :Args:
        :output_file: file name
        :frames: one DataFrames or a list of DataFrames
        :sheets: one sheet name or a list of sheet names
        :kwargs: keyword arguments for ``pd.DataFrame.to_excel()``

    :Usage:
        ::

            # single dataframe and sheet
            .io.xlsave('myReport.xlsx', df, 'raw_data', index=False)
            # multiple dataframes and sheets:
            .io.xlsave(
                'myReportWithManyTabs.xlsx',
                [df_pivot, df],
                ['pivot','raw_data'],
                index=False,
            )

    :Requires:
        ``xlsxwriter``
    """

    with pd.ExcelWriter(
        output_file,
        options = {
            'remove_timezone': True,
        },
    ) as writer:
        _l.info(f'{me()} saving to file {output_file} ...')
        #if only one sheet:
        if isinstance(sheets, str):
            _xlsheet(writer, frames, sheets, **kwargs)
        #if multiple sheets
        else:
            for f, s in zip(frames, sheets):
                _xlsheet(writer, f, s, **kwargs)
        _l.info(f'{me()} done')


#-----------------------------------------------------------------------------
# Reading/Writing Web Pages
#-----------------------------------------------------------------------------

def webtable(df, file, **kwargs):
    """Saves DataFrame as a web table.

    :Args:
        :df: DataFrame
        :file: output file

    :Kwargs:
        :j2template: Jinja2 template (defaults to ``j2/dt_basic.j2.html``)
        :wwwfolder: destination folder (defaults to ``~/www/``)
        :title: webpage title
        :table_class: CSS class of the table
        :table_id: CSS ID of the table
        :header: optional header
        :footer: optional footer
        :scripts: extra scripts (such as Bokeh scripts)
        :content: extra content (such as Bokeh chart)
        :sort_col: sort by column; must escape quote characters,
            *e.g.* ``'5, \"desc\"'``
        :ajax: use server-side rendering with Ajax (for big tables)
        :showurl: if saving to localhost:WEBPORT, display URL to saved webpage
    """

    pd.options.display.max_colwidth = None
    html_params = {
        'j2template': J2_DT_BASIC,
        'wwwfolder': WWWFOLDER,
        'title': 'Stuff',
        'table_class': 'dt',
        'table_id': 'sampledata',
        'header': '',
        'footer': '',
        'content': '',
        'scripts': '',
        'sort_col': '1, \"asc\"',
        'ajax': False,
        'showurl': True,
    }
    html_params.update(**kwargs)

    table_html_empty = df.head(0).to_html(index=False)
    tbody_thead = ''.join(re.split('</?tbody>\n', table_html_empty))
    thead = '\n'.join(re.split('\n', tbody_thead)[1:-1])
    tfoot = re.sub('thead>','tfoot>', thead)

    # for Ajax tables we need just <thead> and <tfoot> elements
    if html_params['ajax']:
        html = '\n'.join([thead, tfoot])
        if not html_params['wwwfolder']:
            url_prefix = ''
        else:
            url_prefix = '/'
        jsonfile = url_prefix + re.sub('html$','json', file)
        df.to_json(
            html_params['wwwfolder']+jsonfile,
            orient='split',
            index=False,
        )
        os.chmod(html_params['wwwfolder']+jsonfile, 0o666)

    # for regular tables we also need <td>'s
    else:
        trtd = re.split('</?tbody>\n', df.to_html(
            index=False,
            escape=False,
        ))[1]
        html = '\n'.join([thead, trtd, tfoot])
        jsonfile = None

    html_params['table_json'] = jsonfile
    html_params['table_html'] = html
    _make_j2html_basic(html_params, file)
    return


def _make_j2html_basic(j2, file):
    """Generates HTML page from a basic.j2 template."""
    # t_loader = FileSystemLoader(searchpath=J2_FOLDER)
    t_loader = PackageLoader(__name__.split('.')[0], package_path='j2')
    t_env = Environment(loader=t_loader)
    t = t_env.get_template(j2['j2template'])
    try:
        outputText = t.render(j2)
        with open(j2['wwwfolder']+file, 'w') as f:
            f.write(outputText)
        os.chmod(j2['wwwfolder']+file, 0o666)
        _l.info('%s published page %s' % (me(), file))

        if j2['showurl']:
            _jupyter_message(j2, file)
    except Exception as e:
        _l.error(f'{me()} {e}')
    return


def _jupyter_message(j2, file):
    """Displays URL and size of an HTML file in Jupyter."""

    try:
        from IPython.core.display import display, HTML
    except ImportError:
        _l.critical('you need IPython/Jupyter for this')
    full_path = j2['wwwfolder'] + file
    size = os.path.getsize(full_path)

    display(HTML(
        f"""Saved as <a href="http://{WEBSERVER}{file}", target=_blank>
            {full_path}</a> \t size: {size} B"""))
    return


#-----------------------------------------------------------------------------
# Reading/Writing Files from Cloud Storage
#-----------------------------------------------------------------------------

def save(stream: Response, outfile: str) -> None:
    """Saves to disk."""

    check_stream(stream)

    with open(outfile, 'wb') as f:
        f.write(stream.content)
    _l.info(f'saved {len(stream.content)} bytes to {outfile}')
    return None


def gunzip_save(stream: Response, outfile: str) -> None:
    """Unzips and saves to disk."""

    check_stream(stream)
    check_stream_is_gzip(stream)

    dec = zlib.decompressobj(32 + zlib.MAX_WBITS)  # skipping gzip header
    f = open(outfile, 'wb')

    try:
        for chunk in stream.iter_content(chunk_size=2**18):
            s = dec.decompress(chunk)
            f.write(s)
        _l.info(f'saved {f.tell()} bytes to {outfile}')
    except StreamConsumedError:
        _l.error('stream consumed, please request again')
    except Exception as e:
        _l.error(f'invalid gzip file: {e}')
    f.close()
    return None


#-----------------------------------------------------------------------------
# Utility Functions
#-----------------------------------------------------------------------------

def check_stream(stream: Response) -> None:
    try:
        assert stream.status_code == 200
    except AssertionError:
        _l.error('bad stream')
    return None


def check_stream_is_gzip(stream: Response) -> None:
    try:
        assert stream.headers['Content-Type'] == 'application/x-gzip'
    except AssertionError:
        _l.error('not a gzip')
    return None
