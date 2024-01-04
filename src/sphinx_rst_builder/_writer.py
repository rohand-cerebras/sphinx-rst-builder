# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-2-Clause
"""Custom docutils writer for ReStructuredText.

"""

from __future__ import (print_function, unicode_literals, absolute_import)

import inspect
import os
import sys
import re
import textwrap
import logging

from docutils import nodes, writers

from sphinx import addnodes
from sphinx.locale import admonitionlabels, versionlabels, _
from sphinx.writers.text import TextTranslator, MAXWIDTH, STDINDENT


_log = logging.getLogger("sphinx_rst_builder.writer")


class RstWriter(writers.Writer):
    supported = ('text',)
    settings_spec = ('No options here.', '', ())
    settings_defaults = {}

    output = None

    def __init__(self, builder):
        writers.Writer.__init__(self)
        self.builder = builder

    def translate(self):
        visitor = RstTranslator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.body


class RstTranslator(TextTranslator):
    sectionchars = '*=-~"+`'

    def __init__(self, document, builder):
        TextTranslator.__init__(self, document, builder)

        newlines = builder.config.text_newlines
        if newlines == 'windows':
            self.nl = '\r\n'
        elif newlines == 'native':
            self.nl = os.linesep
        else:
            self.nl = '\n'
        self.sectionchars = builder.config.text_sectionchars
        self.states = [[]]
        self.stateindent = [0]
        self.list_counter = []
        self.sectionlevel = 0
        self.table = None
        self.table_cur_row = None
        self.table_colspec = None
        self.table_colspan = None
        self.table_rowspan = None
        if self.builder.config.rst_indent:
            self.indent = self.builder.config.rst_indent
        else:
            self.indent = STDINDENT
        self.wrapper = textwrap.TextWrapper(width=STDINDENT, break_long_words=False, break_on_hyphens=False)

    def log_unknown(self, type, node):
        if len(_log.handlers) == 0:
            # Logging is not yet configured. Configure it.
            logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(levelname)-8s %(message)s')
            _log = logging.getLogger("sphinxcontrib.writers.rst")
        _log.warning("%s(%s) unsupported formatting" % (type, node))

    def wrap(self, text, width=STDINDENT):
        self.wrapper.width = width
        return self.wrapper.wrap(text)

    def add_text(self, text):
        self.states[-1].append((-1, text))

    def new_state(self, indent=STDINDENT):
        _log.debug("new_state %s", inspect.stack()[1][3])
        self.states.append([])
        self.stateindent.append(indent)

    def end_state(self, wrap=False, end=[''], first=None):
        _log.debug("end state %s", inspect.stack()[1][3])
        content = self.states.pop()
        maxindent = sum(self.stateindent)
        indent = self.stateindent.pop()
        result = []
        toformat = []
        def do_format():
            if not toformat:
                return
            if wrap:
                res = self.wrap(''.join(toformat), width=MAXWIDTH-maxindent)
            else:
                res = ''.join(toformat).splitlines()
            if end:
                res += end
            result.append((indent, res))
        for itemindent, item in content:
            if itemindent == -1:
                toformat.append(item)
            else:
                do_format()
                result.append((indent + itemindent, item))
                toformat = []
        do_format()
        if first is not None and result:
            itemindent, item = result[0]
            if item:
                result.insert(0, (itemindent - indent, [first + item[0]]))
                result[1] = (itemindent, item[1:])

        self.states[-1].extend(result)

    def visit_document(self, node):
        self.new_state(0)
    def depart_document(self, node):
        self.end_state()
        self.body = self.nl.join(line and (' '*indent + line)
                                 for indent, lines in self.states[0]
                                 for line in lines)
        # TODO: add header/footer?

    def visit_highlightlang(self, node):
        raise nodes.SkipNode

    def visit_section(self, node):
        self._title_char = self.sectionchars[self.sectionlevel]
        self.sectionlevel += 1
    def depart_section(self, node):
        self.sectionlevel -= 1

    def visit_topic(self, node):
        self.new_state(0)
    def depart_topic(self, node):
        self.end_state()

    visit_sidebar = visit_topic
    depart_sidebar = depart_topic

    def visit_rubric(self, node):
        self.new_state(0)
        self.add_text('-[ ')
    def depart_rubric(self, node):
        self.add_text(' ]-')
        self.end_state()

    def visit_compound(self, node):
        # self.log_unknown("compount", node)
        pass
    def depart_compound(self, node):
        pass

    def visit_glossary(self, node):
        # self.log_unknown("glossary", node)
        pass
    def depart_glossary(self, node):
        pass

    def visit_title(self, node):
        if isinstance(node.parent, nodes.Admonition):
            self.add_text(node.astext()+': ')
            raise nodes.SkipNode
        self.new_state(0)
    def depart_title(self, node):
        if isinstance(node.parent, nodes.section):
            char = self._title_char
        else:
            char = '^'
        text = ''.join(x[1] for x in self.states.pop() if x[0] == -1)
        self.stateindent.pop()
        self.states[-1].append((0, ['', text, '%s' % (char * len(text)), '']))

    def visit_subtitle(self, node):
        # self.log_unknown("subtitle", node)
        pass
    def depart_subtitle(self, node):
        pass

    def visit_attribution(self, node):
        self.add_text('-- ')
    def depart_attribution(self, node):
        pass

    def visit_desc(self, node):
        self.new_state(0)
    def depart_desc(self, node):
        self.end_state()

    def visit_desc_signature(self, node):
        if node.parent['objtype'] in ('class', 'exception', 'method', 'function'):
            self.add_text('**')
        else:
            self.add_text('``')
    def depart_desc_signature(self, node):
        if node.parent['objtype'] in ('class', 'exception', 'method', 'function'):
            self.add_text('**')
        else:
            self.add_text('``')

    def visit_desc_name(self, node):
        self.add_text(node.rawsource)
        raise nodes.SkipNode
    def depart_desc_name(self, node):
        pass

    def visit_desc_addname(self, node):
        # self.log_unknown("desc_addname", node)
        pass
    def depart_desc_addname(self, node):
        pass

    def visit_desc_type(self, node):
        # self.log_unknown("desc_type", node)
        pass
    def depart_desc_type(self, node):
        pass

    def visit_desc_returns(self, node):
        self.add_text(' -> ')
    def depart_desc_returns(self, node):
        pass

    def visit_desc_parameterlist(self, node):
        self.add_text('(')
        self.first_param = 1
    def depart_desc_parameterlist(self, node):
        self.add_text(')')

    def visit_desc_parameter(self, node):
        if not self.first_param:
            self.add_text(', ')
        else:
            self.first_param = 0
        self.add_text(node.astext())
        raise nodes.SkipNode

    def visit_desc_optional(self, node):
        self.add_text('[')
    def depart_desc_optional(self, node):
        self.add_text(']')

    def visit_desc_annotation(self, node):
        content = node.astext()
        if len(content) > MAXWIDTH:
            h = int(MAXWIDTH/3)
            content = content[:h] + " ... " + content[-h:]
            self.add_text(content)
            raise nodes.SkipNode
    def depart_desc_annotation(self, node):
        pass

    def visit_refcount(self, node):
        pass
    def depart_refcount(self, node):
        pass

    def visit_desc_content(self, node):
        self.new_state(self.indent)
    def depart_desc_content(self, node):
        self.end_state()

    def visit_figure(self, node):
        self.new_state(self.indent)
    def depart_figure(self, node):
        self.end_state()

    def visit_caption(self, node):
        # self.log_unknown("caption", node)
        pass
    def depart_caption(self, node):
        pass

    def visit_productionlist(self, node):
        self.new_state(self.indent)
        names = []
        for production in node:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        for production in node:
            if production['tokenname']:
                self.add_text(production['tokenname'].ljust(maxlen) + ' ::=')
                lastname = production['tokenname']
            else:
                self.add_text('%s    ' % (' '*len(lastname)))
            self.add_text(production.astext() + self.nl)
        self.end_state(wrap=False)
        raise nodes.SkipNode

    def visit_seealso(self, node):
        self.new_state(self.indent)
    def depart_seealso(self, node):
        self.end_state(first='')

    def visit_footnote(self, node):
        self._footnote = node.children[0].astext().strip()
        self.new_state(len(self._footnote) + self.indent)
    def depart_footnote(self, node):
        self.end_state(first='[%s] ' % self._footnote)

    def visit_citation(self, node):
        if len(node) and isinstance(node[0], nodes.label):
            self._citlabel = node[0].astext()
        else:
            self._citlabel = ''
        self.new_state(len(self._citlabel) + self.indent)
    def depart_citation(self, node):
        self.end_state(first='[%s] ' % self._citlabel)

    def visit_label(self, node):
        raise nodes.SkipNode

    # TODO: option list could use some better styling

    def visit_option_list(self, node):
        # self.log_unknown("option_list", node)
        pass
    def depart_option_list(self, node):
        pass

    def visit_option_list_item(self, node):
        self.new_state(0)
    def depart_option_list_item(self, node):
        self.end_state()

    def visit_option_group(self, node):
        self._firstoption = True
    def depart_option_group(self, node):
        self.add_text('     ')

    def visit_option(self, node):
        if self._firstoption:
            self._firstoption = False
        else:
            self.add_text(', ')
    def depart_option(self, node):
        pass

    def visit_option_string(self, node):
        # self.log_unknown("option_string", node)
        pass
    def depart_option_string(self, node):
        pass

    def visit_option_argument(self, node):
        self.add_text(node['delimiter'])
    def depart_option_argument(self, node):
        pass

    def visit_description(self, node):
        # self.log_unknown("description", node)
        pass
    def depart_description(self, node):
        pass

    def visit_tabular_col_spec(self, node):
        raise nodes.SkipNode

    def visit_colspec(self, node):
        self.table_colspec.append(node['colwidth'])
        raise nodes.SkipNode

    def visit_tgroup(self, node):
        # self.log_unknown("tgroup", node)
        pass
    def depart_tgroup(self, node):
        pass

    def visit_thead(self, node):
        # self.log_unknown("thead", node)
        pass
    def depart_thead(self, node):
        pass

    def visit_tbody(self, node):
        pass
    def depart_tbody(self, node):
        pass

    def visit_row(self, node):
        if len(self.table) <= self.table_cur_row:
            self.table.append([])
    def depart_row(self, node):
        self.table_cur_row += 1

    def visit_entry(self, node):
        self.new_state(0)

    def depart_entry(self, node):
        text = self.nl.join(self.nl.join(x[1]) for x in self.states.pop())
        text = text.replace(self.nl, "")
        self.stateindent.pop()
        self.table[self.table_cur_row].append(text)
        if 'morecols' in node:
            y_index = len(self.table[self.table_cur_row]) - 1
            self.table_colspan[(self.table_cur_row, y_index)] = 1 + node["morecols"]
            self.table[self.table_cur_row] += ["" for _ in range(node["morecols"])]
        if 'morerows' in node:
            y_index = len(self.table[self.table_cur_row]) - 1
            self.table_rowspan[(self.table_cur_row, y_index)] = 1 + node["morerows"]
            self.table += [[""] for _ in range(node["morerows"])]

    def visit_table(self, node):
        if self.table:
            raise NotImplementedError('Nested tables are not supported.')
        self.new_state(0)
        self.table = []
        self.table_colspec = []
        self.table_cur_row = 0
        self.table_colspan = {}
        self.table_rowspan = {}
    def depart_table(self, node):
        # Table drawing code is adapted from from https://stackoverflow.com/a/71655598
        def isInRowspan(y, x, rowspan):
            rowspan_value = 0
            row_i = 0
            for i in range(y):
                if (i, x) in rowspan.keys():
                    rowspan_value = rowspan[(i, x)]
                    row_i = i
            if rowspan_value - (y - row_i) > 0:
                return True
            else:
                return False

        def writeCell(table, y, x, length, rowspan = {}):
            text = table[y][x]
            extra_spaces = ""
            if isInRowspan(y, x, rowspan):
                text = "|"
                for i in range(length): #according to column width
                    text += " "
                return text
            else:
                for i in range(length - len(text) - 2):
                    extra_spaces += " " #according to column width
                return f"| {text} " + extra_spaces

        def writeColspanCell(length, colspan_value): #length argument refers to sum of column widths
            text = ""
            for i in range(length + colspan_value - 1):
                text += " "
            return text

        def getMaxColWidth(table, idx): #find the longest cell in the column to set the column's width
            maxi = 0
            for row in table:
                if len(row) > idx: #avoid index out of range error
                    cur_len = len(row[idx]) + 2
                    if maxi < cur_len:
                        maxi = cur_len
            return maxi

        def getMaxRowLen(table): #find longest row list (in terms of elements)
            maxi = 0
            for row in table:
                cur_len = len(row)
                if maxi < cur_len:
                    maxi = cur_len
            return maxi

        def getAllColLen(table): #collect in a list the widths of each column
            widths = [getMaxColWidth(table, i) for i in range(getMaxRowLen(table))]
            return widths

        def getMaxRowWidth(table): #set the width of the table
            maxi = 0
            for i in range(len(table)):
                cur_len = sum(getAllColLen(table)) + len(getAllColLen(table)) + 1 # "|" at borders and between cells
                if maxi < cur_len:
                    maxi = cur_len
            return maxi

        def drawBorder(table, y, colspan = {}, rowspan = {}):
            col_widths = getAllColLen(table)
            length = getMaxRowWidth(table)
            cell_w_count = 0
            cell_counter = 0
            output = ""
            for i in range(length):
                if isInRowspan(y, cell_counter - 1, rowspan) and not (i == cell_w_count or i == length - 1):
                    output += " "
                elif i == cell_w_count or i == length - 1:
                    output += "+"
                    if cell_counter != getMaxRowLen(table):
                        cell_w_count += col_widths[cell_counter] + 1
                        cell_counter += 1
                else:
                    output += "-"
            output += self.nl
            return output

        def drawTable(table, colspan = {}, rowspan = {}):
            table_width = getMaxRowWidth(table)
            col_widths = getAllColLen(table)
            output = ""
            for y, row in enumerate(table):
                output += drawBorder(table, y, colspan, rowspan)
                x = 0
                while x < len(row): #altered for loop
                    output += writeCell(table, y, x, col_widths[x], rowspan)
                    if (y, x) in colspan.keys():
                        colspan_value = colspan[(y, x)]
                        output += writeColspanCell(sum(col_widths[x+1:x+colspan_value]), colspan_value)
                        x += colspan_value - 1
                    x += 1
                output += "|" + self.nl #end table row
            output += drawBorder(table, getMaxRowLen(table) - 1) #close bottom of table
            return output


        output = drawTable(self.table, self.table_colspan, self.table_rowspan)
        self.add_text(output)

        self.table = None
        self.table_colspec = None
        self.table_rowspan = None
        self.table_colspan = None
        self.end_state(wrap=False)

    def visit_acks(self, node):
        self.new_state(0)
        self.add_text(', '.join(n.astext() for n in node.children[0].children)
                      + '.')
        self.end_state()
        raise nodes.SkipNode

    def visit_image(self, node):
        if 'alt' in node.attributes:
            self.add_text(_('[image: %s]') % node['alt'])
        self.add_text(_('[image]'))
        raise nodes.SkipNode

    def visit_transition(self, node):
        indent = sum(self.stateindent)
        self.new_state(0)
        self.add_text('=' * (MAXWIDTH - indent))
        self.end_state()
        raise nodes.SkipNode

    def visit_bullet_list(self, node):
        self.list_counter.append(-1)
    def depart_bullet_list(self, node):
        self.list_counter.pop()

    def visit_enumerated_list(self, node):
        self.list_counter.append(0)
    def depart_enumerated_list(self, node):
        self.list_counter.pop()

    def visit_definition_list(self, node):
        self.list_counter.append(-2)
    def depart_definition_list(self, node):
        self.list_counter.pop()

    def visit_list_item(self, node):
        if self.list_counter[-1] == -1:
            # bullet list
            self.new_state(indent=2)
        elif self.list_counter[-1] == -2:
            # definition list
            pass
        else:
            # enumerated list
            self.list_counter[-1] += 1
            self.new_state(len(str(self.list_counter[-1])) + self.indent)
    def depart_list_item(self, node):
        if self.list_counter[-1] == -1:
            self.end_state(first='* ', end=None)
        elif self.list_counter[-1] == -2:
            pass
        else:
            self.end_state(first='%s. ' % self.list_counter[-1], end=None)

    def visit_definition_list_item(self, node):
        self._li_has_classifier = len(node) >= 2 and \
                                  isinstance(node[1], nodes.classifier)
    def depart_definition_list_item(self, node):
        pass

    def visit_term(self, node):
        self.new_state(0)
    def depart_term(self, node):
        if not self._li_has_classifier:
            self.end_state(end=None)

    def visit_termsep(self, node):
        self.add_text(', ')
        raise nodes.SkipNode

    def visit_classifier(self, node):
        self.add_text(' : ')
    def depart_classifier(self, node):
        self.end_state(end=None)

    def visit_definition(self, node):
        self.new_state(self.indent)
    def depart_definition(self, node):
        self.end_state()

    def visit_field_list(self, node):
        # self.log_unknown("field_list", node)
        pass
    def depart_field_list(self, node):
        pass

    def visit_field(self, node):
        self.new_state(0)
    def depart_field(self, node):
        self.end_state(end=None)

    def visit_field_name(self, node):
        self.add_text(':')
    def depart_field_name(self, node):
        self.add_text(':')
        content = node.astext()
        self.add_text((16-len(content))*' ')

    def visit_field_body(self, node):
        self.new_state(self.indent)
    def depart_field_body(self, node):
        self.end_state()

    def visit_centered(self, node):
        pass
    def depart_centered(self, node):
        pass

    def visit_hlist(self, node):
        # self.log_unknown("hlist", node)
        pass
    def depart_hlist(self, node):
        pass

    def visit_hlistcol(self, node):
        # self.log_unknown("hlistcol", node)
        pass
    def depart_hlistcol(self, node):
        pass

    def visit_admonition(self, node):
        self.new_state(0)
    def depart_admonition(self, node):
        self.end_state()

    def _visit_admonition(self, node):
        self.new_state(self.indent)
    def _make_depart_admonition(name):
        def depart_admonition(self, node):
            self.end_state(first=admonitionlabels[name] + ': ')
        return depart_admonition

    visit_attention = _visit_admonition
    depart_attention = _make_depart_admonition('attention')
    visit_caution = _visit_admonition
    depart_caution = _make_depart_admonition('caution')
    visit_danger = _visit_admonition
    depart_danger = _make_depart_admonition('danger')
    visit_error = _visit_admonition
    depart_error = _make_depart_admonition('error')
    visit_hint = _visit_admonition
    depart_hint = _make_depart_admonition('hint')
    visit_important = _visit_admonition
    depart_important = _make_depart_admonition('important')
    visit_note = _visit_admonition
    depart_note = _make_depart_admonition('note')
    visit_tip = _visit_admonition
    depart_tip = _make_depart_admonition('tip')
    visit_warning = _visit_admonition
    depart_warning = _make_depart_admonition('warning')

    def visit_versionmodified(self, node):
        self.new_state(0)
        if node.children:
            self.add_text(versionlabels[node['type']] % node['version'] + ': ')
        else:
            self.add_text(versionlabels[node['type']] % node['version'] + '.')

    def depart_versionmodified(self, node):
        self.end_state()

    def visit_literal_block(self, node):
        lang = node.get('language', 'default')
        if node.rawsource != node.astext():
            # most probably a parsed-literal block -- don't highlight
            self.add_text("::")
        elif lang == 'default':
            self.add_text("::")
        else:
            self.add_text(".. code-block:: %s" % lang)
            if self.builder.config.rst_preserve_code_block_flags:
                if node.get('linenos', False):
                    self.add_text("\n   :linenos:")

        self.new_state(self.indent)

    def depart_literal_block(self, node):
        self.end_state(wrap=False)

    def visit_doctest_block(self, node):
        self.new_state(0)
    def depart_doctest_block(self, node):
        self.end_state(wrap=False)

    def visit_line_block(self, node):
        self.new_state(0)
    def depart_line_block(self, node):
        self.end_state(wrap=False)

    def visit_line(self, node):
        # self.log_unknown("line", node)
        pass
    def depart_line(self, node):
        pass

    def visit_block_quote(self, node):
        self.add_text('..')
        self.new_state(self.indent)
    def depart_block_quote(self, node):
        self.end_state()

    def visit_compact_paragraph(self, node):
        pass
    def depart_compact_paragraph(self, node):
        pass

    def visit_paragraph(self, node):
        if not isinstance(node.parent, nodes.Admonition) or \
               isinstance(node.parent, addnodes.seealso):
            self.new_state(0)
    def depart_paragraph(self, node):
        if not isinstance(node.parent, nodes.Admonition) or \
               isinstance(node.parent, addnodes.seealso):
            self.end_state()

    def visit_target(self, node):
        if 'refid' in node:
            self.new_state(0)
            self.add_text('.. _'+node['refid']+':'+self.nl)
    def depart_target(self, node):
        if 'refid' in node:
            self.end_state(wrap=False)

    def visit_index(self, node):
        raise nodes.SkipNode

    def visit_substitution_definition(self, node):
        raise nodes.SkipNode

    def visit_pending_xref(self, node):
        pass
    def depart_pending_xref(self, node):
        pass

    def visit_reference(self, node):
        """Run upon entering a reference

        Because this class inherits from the TextTranslator class,
        regularly defined links, such as::

            `Some Text`_

            .. _Some Text: http://www.some_url.com

        were being written as plaintext. This included internal
        references defined in the standard rst way, such as::

            `Some Reference`

            .. _Some Reference:

            Some Title
            ----------

        To resolve this, if ``refuri`` is not included in the node (an
        internal, non-Sphinx-defined internal uri, the reference is
        left unchanged (e.g. ```Some Text`_`` is written as such).

        If ``internal`` is not in the node (as for an external,
        non-Sphinx URI, the reference is rewritten as an inline link,
        e.g. ```Some Text <http://www.some_url.com>`_``.

        If ``reftitle` is in the node (as in a Sphinx-generated
        reference), the node is converted to an inline link.

        Finally, all other links are also converted to an inline link
        format.
        """
        if 'refuri' not in node:
            if 'name' in node:
                self.add_text('`%s`_' % node['name'])
            elif 'refid' in node:
                # We do not produce the necessary link targets to
                # produce a link here.
                return
            else:
                raise NotImplementedError
            raise nodes.SkipNode
        elif 'internal' not in node:
            if 'name' in node:
                self.add_text('`%s <%s>`_' % (node['name'], node['refuri']))
            else:
                self.add_text('`%s <%s>`_' % (node['refuri'], node['refuri']))
            raise nodes.SkipNode
        elif 'reftitle' in node:
            # Include node as text, rather than with markup.
            # reST seems unable to parse a construct like ` ``literal`` <url>`_
            # Hence we revert to the more simple `literal <url>`_
            self.add_text('`%s <%s>`_' % (node.astext(), node['refuri']))
            # self.end_state(wrap=False)
            raise nodes.SkipNode
        else:
            self.add_text('`%s <%s>`_' % (node.astext(), node['refuri']))
            raise nodes.SkipNode

    def depart_reference(self, node):
        if 'refuri' not in node:
            pass # Don't add these anchors
        elif 'internal' not in node:
            pass # Don't add external links (they are automatically added by the reST spec)
        elif 'reftitle' in node:
            pass

    def visit_download_reference(self, node):
        self.log_unknown("download_reference", node)
        pass
    def depart_download_reference(self, node):
        pass

    def visit_emphasis(self, node):
        self.add_text('*')
    def depart_emphasis(self, node):
        self.add_text('*')

    def visit_literal_emphasis(self, node):
        self.add_text('*')
    def depart_literal_emphasis(self, node):
        self.add_text('*')

    def visit_strong(self, node):
        self.add_text('**')
    def depart_strong(self, node):
        self.add_text('**')

    def visit_abbreviation(self, node):
        self.add_text('')
    def depart_abbreviation(self, node):
        if node.hasattr('explanation'):
            self.add_text(' (%s)' % node['explanation'])

    def visit_title_reference(self, node):
        # self.log_unknown("title_reference", node)
        self.add_text('*')
    def depart_title_reference(self, node):
        self.add_text('*')

    def visit_literal(self, node):
        self.add_text('``')
    def depart_literal(self, node):
        self.add_text('``')

    def visit_subscript(self, node):
        self.add_text('_')
    def depart_subscript(self, node):
        pass

    def visit_superscript(self, node):
        self.add_text('^')
    def depart_superscript(self, node):
        pass

    def visit_footnote_reference(self, node):
        self.add_text('[%s]' % node.astext())
        raise nodes.SkipNode

    def visit_citation_reference(self, node):
        self.add_text('[%s]' % node.astext())
        raise nodes.SkipNode

    def visit_Text(self, node):
        self.add_text(node.astext())
    def depart_Text(self, node):
        pass

    def visit_generated(self, node):
        # self.log_unknown("generated", node)
        pass
    def depart_generated(self, node):
        pass

    def visit_inline(self, node):
        # self.log_unknown("inline", node)
        pass
    def depart_inline(self, node):
        pass

    def visit_problematic(self, node):
        self.add_text('>>')
    def depart_problematic(self, node):
        self.add_text('<<')

    def visit_system_message(self, node):
        self.new_state(0)
        self.add_text('<SYSTEM MESSAGE: %s>' % node.astext())
        self.end_state()
        raise nodes.SkipNode

    def visit_comment(self, node):
        raise nodes.SkipNode

    def visit_meta(self, node):
        # only valid for HTML
        raise nodes.SkipNode

    def visit_raw(self, node):
        if 'text' in node.get('format', '').split():
            self.body.append(node.astext())
        raise nodes.SkipNode

    def unknown_visit(self, node):
        raise NotImplementedError('Unknown node: ' + node.__class__.__name__)
