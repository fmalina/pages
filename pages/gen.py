import os
import shutil
import brotli
import click
from jinja2 import Environment, PackageLoader, FileSystemLoader

from pages.models import Page


@click.command()
@click.option('--source', default='.', help='Source folder with markdown files')
@click.option('--target', default='_static', help='Destination folder for static site')
@click.option('--tpl', default='pages', help='Custom template folder')
@click.option('--ext', default='.htm', help='File extension')
def generate_site(source, target, tpl, ext, more_context={}):
    """Pages: static site generator"""
    pages = [Page(path) for path in Page.list(source)]
    if tpl == 'pages':
        loader = PackageLoader(tpl)
    else:
        loader = FileSystemLoader(tpl)
    tpl_env = Environment(loader=loader)
    if not os.path.exists(target):
        os.makedirs(target)
    for p in pages:
        content = render_page(p, pages, tpl_env, more_context).encode()
        generate_page(target, path=f'{p.get_absolute_url}{ext}', content=content)
    feed = render_feed(pages, tpl_env, more_context, tpl='pages/feed.xml').encode()
    smap = render_feed(pages, tpl_env, more_context, tpl='pages/sitemap.xml').encode()
    generate_page(target, path='/feed.xml', content=feed)
    generate_page(target, path='/sitemap-pages.xml', content=smap)


def generate_page(static_root, path, content):
    """Utility to write and brotli compress a pages
    given a server static root, URL path and pages content"""
    no_leading_slash = str(path)[1:]
    full_path = os.path.join(static_root, no_leading_slash)
    if '/' in path[1:]:
        folder = os.path.join(static_root, *path.split('/')[1:-1])
        if not os.path.exists(folder):
            os.makedirs(folder)
    if path.endswith('/'):
        full_path = full_path + 'index.html'
    with open(full_path, 'wb+') as f:
        f.write(content)
    with open(full_path + '.br', 'wb+') as cf:
        compressed = brotli.compress(content)
        cf.write(compressed)


def date_sort(ls):
    return sorted(ls, key=lambda x: x.created, reverse=True)


def render_page(page, all_pages, tpl_env, more_context, tpl='pages/page.html'):
    tpl = tpl_env.get_template(tpl)
    # nav list
    ls = []
    if page.slug in ['blog', 'help', 'activism']:
        ls = list(page.list(page.path))
        # pick nav pages out of full list
        ls = [x for x in all_pages if x.path in ls]
        # order blog entries by date
        if page.parent == 'blog':
            ls = date_sort(ls)
    print(page.get_absolute_url)  # ls[:3]
    return tpl.render(page=page, ls=ls, desc=page.desc, **more_context)


def render_feed(all_pages, tpl_env, more_context, tpl):
    all_pages = date_sort(all_pages)
    tpl = tpl_env.get_template(tpl)
    return tpl.render(pages=all_pages, **more_context)


def delete_folders(folders, root):
    """Delete static files caches for all sites used by."""
    for folder_name in folders:
        try:
            path = os.path.join(root, folder_name)
            shutil.rmtree(path, ignore_errors=True)
        except FileNotFoundError:
            pass


def delete_files(paths):
    """Delete files from a list of paths"""
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
