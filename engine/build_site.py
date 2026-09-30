"""Rebuild the website: runs the rating engine, then writes ../index.html."""
import json, runpy, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
runpy.run_path('build_site_data.py', run_name='__main__')
a = json.load(open('brand_assets.json'))
d = open('site_data.json').read().replace('</', '<\\/')
page = open('site_template.html').read().replace('__DATA__', d).replace('__ICON__', a['icon']).replace('__HEADER__', a['header'])
doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       '<link rel="icon" href="favicon.png">\n' + page + '\n</html>\n')
open('../index.html', 'w').write(doc)
print('index.html written')
