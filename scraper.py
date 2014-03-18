#!/usr/bin/env python

from bs4 import BeautifulSoup
from dateutil import parser
import re
import requests
import scraperwiki
import urlparse

class Page:
    def __init__(self, path, basename, encoding):
        self.path = path
        self.basename = basename
        self.encoding = encoding
        self.url = path + basename

class Archive(Page):
    def __init__(self, path, basename, encoding):
        Page.__init__(self, path, basename, encoding)

    @property
    def links(self):
        link_re = 'ap[0-9]+\.html'
        soup = make_soup(self.url, self.encoding, parser='html.parser')
        return soup.find_all(href=re.compile(link_re))

class Entry(Page):
    def __init__(self, path, basename, encoding, link):
        Page.__init__(self, path, basename, encoding)
        self.link = link

    @property
    def entry_url(self):
        return self.url

    @property
    def date(self):
        date_raw = self.link.previous_sibling[:-3]
        date = parser.parse(date_raw).strftime('%Y-%m-%d')
        return unicode(date, 'UTF-8')

    @property
    def title(self):
        return self.link.text

    @property
    def explanation(self):
        soup = make_soup(self.url, self.encoding, True, self.path)
        html = str(soup)
        explanation_with_linebreaks = re.search('<(b|(h3))>.*?Explanation.*?</(b|(h3))>\s*(.*?)\s*(</p>)?<p>', html, re.DOTALL | re.IGNORECASE).group(5)
        explanation_without_linebreaks = re.sub('\s+', ' ', explanation_with_linebreaks)
        return unicode(explanation_without_linebreaks, 'UTF-8')

    @property
    def picture_url(self):
        soup = make_soup(self.url, self.encoding, True, self.path)
        picture_link = soup.find(href=re.compile(self.path.replace('.', '\.') + 'image/'))

        # Check that there is a picture (APOD sometimes publishes videos instead).
        if picture_link:
            picture_url = picture_link['href']
        else:
            picture_url = ''

        return unicode(picture_url, 'UTF-8')

def make_soup(url, encoding, absolute=False, base='', parser=None):
    html = requests.get(url)

    if parser:
        soup = BeautifulSoup(html.content, parser, from_encoding=encoding)
    else:
        soup = BeautifulSoup(html.content, from_encoding=encoding)

    # Make all links absolute.
    # http://stackoverflow.com/a/4468467/715866
    if absolute:
        for a in soup.find_all('a', href=True):
            a['href'] = urlparse.urljoin(base, a['href'])

    return soup

def save(url, date, title, explanation, picture_url):
    primary_keys = ['url']
    data = {'url': url, 'date': date, 'title': title, 'explanation': explanation, 'picture_url': picture_url}
    scraperwiki.sql.save(primary_keys, data)

def main():
    path = 'http://apod.nasa.gov/apod/'
    site_encoding = 'windows-1252'
    archive = Archive(path, 'archivepix.html', site_encoding)

    for link in archive.links:
        entry = Entry(path, link['href'], site_encoding, link)

        # APOD sometimes publishes videos instead. Don't save those.
        if entry.picture_url:
            save(entry.entry_url, entry.date, entry.title, entry.explanation, entry.picture_url)

if __name__ == '__main__':
    main()
