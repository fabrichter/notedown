import os
import sys
import argparse
import pkg_resources

from .notedown import (MarkdownReader,
                       MarkdownWriter,
                       JSONReader,
                       JSONWriter,
                       Knitr)


markdown_template \
    = pkg_resources.resource_filename('notedown',
                                      'templates/markdown.tpl')
markdown_figure_template \
    = pkg_resources.resource_filename('notedown',
                                      'templates/markdown_outputs.tpl')


def run(notebook):
    """Run a notebook using runipy."""
    try:
        from runipy.notebook_runner import NotebookRunner
    except ImportError:
        raise('You need runipy installed to run notebooks!'
              'try `pip install runipy`')

    runner = NotebookRunner(notebook)
    runner.run_notebook()


examples = """
Example usage of notedown
-------------------------

Convert markdown into notebook:

    notedown input.md > output.ipynb

    notedown input.md --output output.ipynb


Convert a notebook into markdown, with outputs intact:

    notedown input.ipynb --from notebook --to markdown > output_with_outputs.md


Convert a notebook into markdown, stripping all outputs:

    notedown input.ipynb --from notebook --to markdown --strip > output.md


Strip the output cells from markdown:

    notedown with_output_cells.md --to markdown --strip > no_output_cells.md


Convert from markdown and execute using runipy:

    notedown input.md --run > executed_notebook.ipynb


Convert r-markdown into markdown:

    notedown input.Rmd --to markdown --knit > output.md


Convert r-markdown into an IPython notebook:

    notedown input.Rmd --knit > output.ipynb


Convert r-markdown into a notebook with the outputs computed, using
the rmagic extension to execute the code blocks:

    notedown input.Rmd --knit --rmagic --run > executed_output.ipynb
"""


def cli():
    """Execute for command line usage."""
    description = "Create an IPython notebook from markdown."
    example_use = "Example:  notedown some_markdown.md > new_notebook.ipynb"
    parser = argparse.ArgumentParser(description=description,
                                     epilog=example_use)
    parser.add_argument('input_file',
                        help="markdown input file (default STDIN)",
                        nargs="?",
                        type=argparse.FileType('r'),
                        default=sys.stdin)
    parser.add_argument('--output',
                        help="output file, (default STDOUT)",
                        type=argparse.FileType('w'),
                        default=sys.stdout)
    parser.add_argument('--from',
                        dest='informat',
                        choices=('notebook', 'markdown'),
                        help=("format to convert from, defaults to markdown "
                              "or file extension"))
    parser.add_argument('--to',
                        dest='outformat',
                        choices=('notebook', 'markdown'),
                        help=("format to convert to, defaults to notebook "
                              "or file extension"))
    parser.add_argument('--reverse',
                        action='store_true',
                        help=("alias for --from notebook --to markdown"))
    parser.add_argument('--run',
                        action='store_true',
                        help=("run the notebook using runipy"))
    parser.add_argument('--strip',
                        action='store_true',
                        dest='strip_outputs',
                        help=("strip output cells"))
    parser.add_argument('--precode',
                        nargs='+',
                        default=[],
                        help=("additional code to place at the start of the "
                              "notebook, e.g. --pre '%%matplotlib inline' "
                              "'import numpy as np'"))
    parser.add_argument('--knit',
                        nargs='?',
                        help=("pre-process the markdown with knitr. "
                              "Default chunk options are 'eval=FALSE' "
                              "but you can change this by passing a string. "
                              "Requires R in your path and knitr installed."),
                        const='eval=FALSE')
    parser.add_argument('--rmagic',
                        action='store_true',
                        help=("autoload the rmagic extension. Synonym for "
                              "--precode '%%load_ext rmagic'"))
    parser.add_argument('--nomagic',
                        action='store_false',
                        dest='magic',
                        help=("disable code magic."))
    parser.add_argument('--examples',
                        help=('show example usage'),
                        action='store_true')
    parser.add_argument('--figures',
                        help=('turn outputs into figures'),
                        action='store_true')
    parser.add_argument('--template',
                        help=('template file'))

    args = parser.parse_args()

    if args.examples:
        print examples
        exit()

    # if no stdin and no input file
    if args.input_file.isatty():
        parser.print_help()
        exit()

    # pre-process markdown by using knitr on it
    if args.knit:
        knitr = Knitr()
        input_file = knitr.knit(args.input_file, opts_chunk=args.knit)
    else:
        input_file = args.input_file

    if args.rmagic:
        args.precode.append(r"%load_ext rmagic")

    if args.figures:
        template_file = markdown_figure_template
    else:
        template_file = markdown_template

    template_file = args.template or template_file

    # reader and writer classes with args and kwargs to
    # instantiate with
    readers = {'notebook': (JSONReader, [], {}),
               'markdown': (MarkdownReader,
                            [],
                            {'precode': '\n'.join(args.precode),
                             'magic': args.magic})
               }
    writers = {'notebook': (JSONWriter, [args.strip_outputs], {}),
               'markdown': (MarkdownWriter,
                            [template_file, args.strip_outputs],
                            {'write_outputs': args.figures})
               }

    if args.reverse:
        args.informat = 'notebook'
        args.outformat = 'markdown'

    informat = args.informat or ftdetect(args.input_file.name) or 'markdown'
    outformat = args.outformat or ftdetect(args.output.name) or 'notebook'

    Reader, rargs, rkwargs = readers[informat]
    Writer, wargs, wkwargs = writers[outformat]
    reader = Reader(*rargs, **rkwargs)
    writer = Writer(*wargs, **wkwargs)

    with input_file as ip, args.output as op:
        notebook = reader.read(ip)
        if args.run:
            run(notebook)
        writer.write(notebook, op)


def ftdetect(filename):
    """Determine if filename is markdown or notebook,
    based on the file extension.
    """
    _, extension = os.path.splitext(filename)
    md_exts = ['.md', '.markdown', '.mkd', '.mdown', '.mkdn', '.Rmd']
    nb_exts = ['.ipynb']
    if extension in md_exts:
        return 'markdown'
    elif extension in nb_exts:
        return 'notebook'
    else:
        return None


if __name__ == '__main__':
    cli()
