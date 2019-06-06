from requests import get, post
from bs4 import BeautifulSoup
import re

from lingcorpora.params_container import Container
from lingcorpora.target import Target
from lingcorpora.exceptions import EmptyPageException

class PageParser(Container):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tag_variable = 'slt' if self.get_analysis else 's'
        left = 5 if not self.n_left else self.n_left
        right = 5 if not self.n_right else self.n_right
        if not self.subcorpus:
            self.subcorpus = 'nkjp300'
        self.data = {
            'show_in_match': tag_variable,
            'show_in_context': tag_variable,
            'left_context_width': left,
            'right_context_width': right,
            'wide_context_width': '50',
            'results_per_page': self.n_results,
            'next': '/poliqarp/{}/query/'.format(self.subcorpus)
        }
    
    def _get_html(self):
        s = post(url='http://nkjp.pl/poliqarp/settings/', data=self.data)
        if s.status_code != 200:
            raise EmptyPageException
        
        user_agent = {
            'Host': 'nkjp.pl',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.' \
                '10; rv:51.0) Gecko/20100101 Firefox/51.0',
            'Accept': 'text/html,application/xhtml+xml,application/' \
                'xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'http://nkjp.pl/poliqarp',
            'Cookie': 'sessionid={}'.format(s.cookies.get('sessionid')),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        post(
            url='http://nkjp.pl/poliqarp/query/',
            headers=user_agent,
            data={'query': self.query,
                  'corpus': self.subcorpus},
        )
        request = post(
            url='http://nkjp.pl/poliqarp/{}/query/export/'.format(self.subcorpus),
            headers=user_agent,
            data={'format': 'html'},
        )
        html_page = request
        return html_page.text
    
    def _parse(self):
        html = self._get_html()
        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table')
        rows = table.select('tr')
        results = []
        for row in rows:
            r = row.select('td')
            results.append([r[0].text, r[1].text, r[2].text])
        return results[:self.n_results]
    
    def _parse_analysis(self, word):
        analysis_text = re.findall('\[(.*?)\]', word)[0]
        analysis_list = analysis_text.split(':')
        analysis_dict = {
            'lex': analysis_list[0],
            'gram': analysis_list[1:],
        }
        token = re.findall('(.*?) \[', word)[0]
        return token, analysis_dict
    
    def _new_target(self, r):
        if self.get_analysis:
            with_analysis = self._parse_analysis(r[1])
            r[1] = with_analysis[0]
            analysis = with_analysis[1]
            r[0] = ' '.join([w for w in r[0].split() if not w.startswith('[')])
            r[2] = ' '.join([w for w in r[2].split() if not w.startswith('[')])
        else:
            analysis = {}
        target = Target(
            text='{} {} {}'.format(*r).replace('  ', ' '),
            idxs=(len(r[0]) + 2, len(r[0]) + len(r[1])),
            meta='',
            analysis=analysis,
        )
        return target
    
    def extract(self):
        res = self._parse()
        for r in res:
            yield self._new_target(r)
