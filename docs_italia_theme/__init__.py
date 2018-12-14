# coding=utf-8

"""Docs Italia theme"""

import os
import sys
import re
import yaml
import json

from docutils.nodes import figure
from docutils.nodes import table
from docutils.nodes import bullet_list
from docutils.nodes import list_item
from docutils.nodes import reference
from docutils.nodes import caption
from docutils.nodes import Text
from sphinx.addnodes import compact_paragraph
from sphinx.addnodes import glossary
from sphinx.addnodes import toctree
from sphinx.environment.adapters.toctree import TocTree

# This part would be better placed as an extension:
# It loads yaml data files to set them as variables
def get_html_theme_path():
    """Return list of HTML theme paths."""
    cur_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return cur_dir


def deep_merge(source, destination):
    """Deep merge dictionaries"""
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination


def load_theme_data():
    """Load data from YAML config file"""
    source_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'data')
    )
    config_path = os.path.join(source_path, '_config.yml')
    data_path = os.path.join(source_path, '_data')
    context = {}

    # Load site config
    config_h = open(config_path)
    config_data = yaml.load(config_h)
    context.update(config_data)

    # Load Jekyll data files
    filename_re = re.compile('\.yml$')
    context['data'] = {}
    for filename in os.listdir(data_path):
        if filename_re.search(filename):
            datafile_source = filename_re.sub('', filename)
            datafile_path = os.path.join(data_path, filename)
            datafile_h = open(datafile_path)
            datafile_data = yaml.load(datafile_h)
            context['data'].update({datafile_source: datafile_data})

    # Transform network links to ordered mapping. Doing this dynamically
    # instead of with overrides to alter mapping into an ordered list and keep
    # the existing data
    network_links = []
    for link in ['trasformazione_digitale', 'developers', 'design', 'forum',
                 'docs', 'github']:
        link_data = context['data']['network_links'].get(link, {}).copy()
        link_data['name'] = link

        # Alter classes
        class_str = link_data.get('class', '')
        classes = class_str.split(' ')
        try:
            del classes[classes.index('current')]
        except (IndexError, ValueError):
            pass
        if link == 'docs':
            classes.append('current')
        link_data['class'] = ' '.join(classes)

        network_links.append(link_data)
    context['data']['network_links'] = network_links

    footer_links = []
    for link in ['privacy', 'legal']:
        link_data = context['data']['footer_links'].get(link, {}).copy()
        footer_links.append(link_data)
    context['data']['footer_links'] = footer_links

    return context

def add_context_data(app, pagename, templatename, context, doctree):
    """Add yaml data to Sphinx context"""
    context['site'] = app.site_data
    # The translation context is pinned to the Italian sources, as Sphinx has
    # it's own translation mechanism built in
    if 'language' in context and context['language'] != None:
        language = context['language']
    else:
        language = app.site_data['default_language']
    context['t'] = app.site_data['data']['l10n'][language]['t']

    # Run only for local development
    if os.environ.get('READTHEDOCS', None) != 'True':
        context['LOCAL'] = True
        context['PRODUCTION_DOMAIN'] = 'localhost'
        context['slug'] = 'demo-document'
        context['current_version'] = 'bozza'
        context['rtd_language'] = 'it'
        context['publisher_project'] = u'Progetto demo'
        context['publisher_project_slug'] = 'progetto-demo'
        context['publisher'] = u'Organizzazione demo'
        context['publisher_slug'] = 'organizzazione-demo'
        context['tags'] = [
            ('demo', '#'),
            ('docs italia', '#')
        ]

    if 'docsitalia_data' in context:
        context['docstitle'] = context['docsitalia_data']['document']['name']
    else:
        try:
            with open(os.path.join(app.builder.srcdir,'document_settings.yml')) as document_settings:
                data = document_settings.read()
                data = yaml.safe_load(data)
        except:
            data = {
                'document': {
                    'name': 'Titolo del documento non impostato'
                }
            }

        context['docsitalia_data'] = data

def generate_additonal_tocs(app, pagename, templatename, context, doctree):
    """Generate and add additional tocs to Sphinx context"""
    pages_list = []
    content_tocs = []
    glossary_tocs = []
    content_toc = ''
    glossary_toc = ''
    figures_toc = bullet_list()
    tables_toc = bullet_list()
    index = app.env.config.master_doc
    doctree_index = app.env.get_doctree(index)

    for toctreenode in doctree_index.traverse(toctree):
        toctree_element = TocTree(app.env).resolve(pagename, app.builder, toctreenode, includehidden=True)
        try:
            toc_caption = next(child for child in toctree_element.children if isinstance(child, caption))
            toctree_element.children.remove(toc_caption)
        except StopIteration:
            pass
        except AttributeError:
            continue
        if 'glossary_toc' in toctreenode.parent.attributes['names']:
            glossary_tocs.append(toctree_element)
        else:
            content_tocs.append(toctree_element)
            pages_list = toctreenode['includefiles']

    if content_tocs:
        content_toc = content_tocs[0]
        for content_element in content_tocs[1:]:
            try:
                content_toc.extend(content_element.children)
            except AttributeError:
                continue
    if glossary_tocs:
        glossary_toc = glossary_tocs[0]
        for glossary_element in glossary_tocs[1:]:
            glossary_toc.extend(glossary_element.children)
        glossary_toc = glossary_toc.children[0].children[0].children[1]

    pages_with_fignumbers = (x for x in pages_list if x in app.env.toc_fignumbers)
    for page in pages_with_fignumbers:
        doctree_page = app.env.get_doctree(page)

        for figurenode in doctree_page.traverse(figure):
            if not figurenode.attributes['ids']:
                continue
            figure_id = figurenode.attributes['ids'][0]
            toc_fig_tables = app.env.toc_fignumbers[page].get('figure', {})
            figure_number = toc_fig_tables.get(figure_id)
            if figure_number is None:
                continue
            figure_title = figurenode.children[0].get('alt') or context['t']['no_description']
            try:
                figure_text_string = 'Fig. {}.{} - {}'.format(
                    figure_number[0], figure_number[1], figure_title)
            except IndexError:
                continue
            figure_text = Text(figure_text_string)
            figure_text.rawsource = figure_text_string
            figure_reference = reference()
            figure_reference.attributes['internal'] = True
            figure_reference.attributes['refuri'] = app.builder.get_relative_uri(pagename, page) + '#' + figure_id
            figure_compact_paragraph = compact_paragraph()
            figure_list_item = list_item()
            figure_text.parent = figure_reference
            figure_reference.children.append(figure_text)
            figure_reference.parent = figure_compact_paragraph
            figure_compact_paragraph.children.append(figure_reference)
            figure_compact_paragraph.parent = figure_list_item
            figure_list_item.children.append(figure_compact_paragraph)
            figure_list_item.parent = figures_toc
            figures_toc.children.append(figure_list_item)

        for tablenode in doctree_page.traverse(table):
            if not tablenode.attributes['ids']:
                continue
            table_id = tablenode.attributes['ids'][0]
            toc_fig_tables = app.env.toc_fignumbers[page].get('table', {})
            table_number = toc_fig_tables.get(table_id)
            if table_number is None:
                continue
            table_title = tablenode.children[0].rawsource if tablenode.children[0].rawsource else context['t']['no_description']
            table_title = (table_title[:60] + '...') if len(table_title) > 60 else table_title
            table_text_string = 'Tab. ' + '.'.join([str(n) for n in table_number]) + ' - ' + table_title
            table_text = Text(table_text_string)
            table_text.rawsource = table_text_string
            table_reference = reference()
            table_reference.attributes['internal'] = True
            table_reference.attributes['refuri'] = app.builder.get_relative_uri(pagename, page) + '#' + table_id
            table_compact_paragraph = compact_paragraph()
            table_list_item = list_item()
            table_text.parent = table_reference
            table_reference.children.append(table_text)
            table_reference.parent = table_compact_paragraph
            table_compact_paragraph.children.append(table_reference)
            table_compact_paragraph.parent = table_list_item
            table_list_item.children.append(table_compact_paragraph)
            table_list_item.parent = tables_toc
            tables_toc.children.append(table_list_item)

    context['content_toc'] = app.builder.render_partial(content_toc)['fragment'] if hasattr(content_toc, 'children') and content_toc.children else None
    context['glossary_toc'] = app.builder.render_partial(glossary_toc)['fragment'] if hasattr(glossary_toc, 'children') and glossary_toc.children else None
    context['figures_toc'] = app.builder.render_partial(figures_toc)['fragment'] if hasattr(figures_toc, 'children') and figures_toc.children else None
    context['tables_toc'] = app.builder.render_partial(tables_toc)['fragment'] if hasattr(tables_toc, 'children') and tables_toc.children else None

def generate_glossary_json(app, doctree, docname):
    """Generate glossary JSON file"""
    current_builder = app.builder.name
    if current_builder == 'html' or current_builder == 'readthedocs':
        glossary_data = {}
        data_dir = app.outdir + '/_static/data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        if os.path.exists(data_dir + '/glossary.json'):
            with open(data_dir + '/glossary.json', 'r') as existing_glossary:
                glossary_data = json.loads(existing_glossary.read())
        for node in doctree.traverse(glossary):
            for definition_list in node.children:
                for definition_list_item in definition_list.children:
                    term = definition_list_item.children[0].rawsource
                    definition = ''
                    for paragraphs in definition_list_item.children[1].children:
                        definition += paragraphs.rawsource + '\n'
                    definition = definition[:-2]
                    glossary_data[term] = definition
        glossary_json = json.dumps(glossary_data)
        glossary_json_file = open(data_dir + '/glossary.json', 'w')
        glossary_json_file.write(glossary_json)
        glossary_json_file.close()

def glossary_page_id(app, doctree, docname):
    glossary_pages = []
    index = app.env.config.master_doc
    doctree_index = app.env.get_doctree(index)

    for toctreenode in doctree_index.traverse(toctree):
        toctree_element = TocTree(app.env).resolve(index, app.builder, toctreenode, includehidden=True)
        if 'glossary_toc' in toctreenode.parent.attributes['names']:
            glossary_pages = toctreenode['includefiles']

    if docname in glossary_pages:
        for glossary_section in doctree.children:
            glossary_section.attributes['ids'] = ['glossary-page']

##############################
# Define the new custom node #
##############################
from docutils import nodes

###################################
# Define the new custom directive #
###################################
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives

class DiscourseCommentsNode(nodes.Structural, nodes.Element):
    @staticmethod
    def visit(self, node):
        pass
    @staticmethod
    def depart(self, node):
        pass

class DiscourseCommentsDirective(Directive):
    # Directive's parameters
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        'topic_id': directives.unchanged
    }
    final_argument_whitespace = True

    def run(self):
        settings = self.state.document.settings
        lang_code = settings.language_code
        env = settings.env

        # Stored configs
        config = env.config
        # Directive's options
        options = self.options

        node = DiscourseCommentsNode()

        #############
        # Templates #
        #############

        # Form for write new comment
        form_template = """
            <div class='box-comment-""" + options['topic_id'] + """ box-comment' data-topic='""" + options['topic_id'] + """'>
                <div class="form group">
                    <div class="box-comment__errors-box"></div>
                    <!-- Write -->
                    <div class="row align-items-center mt-4 mb-4 block-comments__input box-comment__write">
                        <figure class="col-auto mb-0">
                            <img class="block-comments__img box-comment__figure rounded-circle" src="">
                            <figcaption>
                                <!-- <a href='#logout' class="block-comments__logout-link block-comments__logout-link--icon" alt="Logout">&#10060;</a> -->
                                <a href='#logout' class="block-comments__logout-link block-comments__logout-link--visible" data-toggle="modal" data-target="#logout-modal" title="Logout" alt="Logout">Logout</a>
                            </figcaption>
                        </figure>
                        <textarea class='form-control box-comment__body col ml-2 p-2' id="comments-input" placeholder='Scrivi qui un commento. Per formattare il testo puoi usare Markdown, clicca sul bottone "suggerimenti" per vedere degli esempi.' rows="4"></textarea>
                    </div>
                    <!-- Buttons -->
                    <div class='box-comment__buttons'>
                        <button type='submit' class='btn btn-primary btn-sm box-comment__submit mr-2' disabled='true'><div>invia</div></button>
                        <button type="button" class="btn btn-sm btn-secondary new-comment__suggestions" data-container="body" data-toggle="popover" data-content="html">suggerimenti</button><span class="loading no-bg">&nbsp;</span>
                    </div>
                    <div class="box-comment__required">
                        <span>Scrivi almeno altri <span class='required-chars'></span> caratteri</span>
                    </div>
                </div>
            </div>
        """
        cbox_template = """
            <div class="block-comments container-fluid" id='accordion-comments-""" + options['topic_id'] + """'>
                <!-- Top header -->
                <div class="block-comments__header border-top border-bottom border-width-2 pt-3 pb-3 row align-items-center justify-content-between">
                    <h6 class="col-auto text-uppercase mb-0">Commenti</h6>
                    <button class="col-auto block-comments__toggle-btn rounded-circle border border-medium-blue border-width-2" data-toggle="collapse" data-target='#comments-""" + options['topic_id'] + """' aria-expanded="true"><span class="docs-icon-plus"></span><span class="docs-icon-minus"></span></button>
                </div>
            </div>
            <div class="block-comments__body collapse show" data-parent='#accordion-comments-""" + options['topic_id'] + """' id='comments-""" + options['topic_id'] + """'>
                <!-- Input row -->
                <div class="d-flex align-items-center mt-4 mb-4 block-comments__input">
                    """ + form_template + """
                </div>
                <div class="row">
                    <div class="block-comments__list col">
                        <div class="row mt-4 mb-4">
                            <ul class="block-comments__list col items" id="accordion-comment-item" data-topic='"""+ options['topic_id'] +"""'></ul>
                        </div>
                    </div>
                </div>
            </div>
        """

        # Create logout modal
        logout_modal = """
            <div class="modal logout-modal" id="logout-modal" tabindex="-1" role="dialog">
              <div class="modal-dialog" role="document">
                <div class="modal-content">
                  <div class="modal-header">
                    <h5 class="modal-title">Esegui il logout</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                      <span aria-hidden="true">&times;</span>
                    </button>
                  </div>
                  <div class="modal-body">
                    <p> Dopo il logout non sar&agrave; possibile scrivere nuovi commenti. Sei sicuro di voler procedere? </p>
                  </div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-primary" id="logout-modal__submit">Conferma</button>
                    <button type="button" class="btn btn-secondary" data-dismiss="modal" id="logout-modal__cancel">Annulla</button>
                  </div>
                </div>
              </div>
            </div>
        """
        # Create "account suspended" modal
        suspended_modal = """
            <div class="modal suspended-modal" id="suspended-modal" tabindex="-1" role="dialog">
              <div class="modal-dialog" role="document">
                <div class="modal-content">
                  <div class="modal-header">
                    <h5 class="modal-title">Account sospeso</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                      <span aria-hidden="true">&times;</span>
                    </button>
                  </div>
                  <div class="modal-body">
                    <p> Il tuo account e&grave; stato sospeso, se ti serve aiuto vieni a trovarci sul workspace Slack di Developers Italia. </p>
                  </div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal" id="logout-modal__cancel">Chiudi</button>
                  </div>
                </div>
              </div>
            </div>
        """

        node += nodes.raw(text=cbox_template, format='html')
        node += nodes.raw(text=logout_modal, format='html')
        node += nodes.raw(text=suspended_modal, format='html')

        node['data-topic-id'] = options['topic_id']

        return [ node ]


def setup(app):
    app.site_data = load_theme_data()
    app.add_html_theme('docs_italia_theme', os.path.abspath(os.path.dirname(__file__)))
    app.connect('html-page-context', add_context_data)
    app.connect('html-page-context', generate_additonal_tocs)
    app.connect('doctree-resolved', generate_glossary_json)
    app.connect('doctree-resolved', glossary_page_id)
    # Setup for forum_italia custom directive
    app.add_node(DiscourseCommentsNode,
        html=(DiscourseCommentsNode.visit, DiscourseCommentsNode.depart),
        latex=(DiscourseCommentsNode.visit, DiscourseCommentsNode.depart)
    )
    app.add_directive('forum_italia', DiscourseCommentsDirective)
    
