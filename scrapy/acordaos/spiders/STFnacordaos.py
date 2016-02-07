# -*- coding: utf-8 -*-
from scrapy.selector import Selector
from scrapy.spiders import Spider
import re
from acordaos.items import AcordaoItem

FILE_NDOCS='temp'
class STFSpider(Spider):

    name = 'stf_get_nacordaos'
    
    def __init__ ( self, iDate, fDate):
        self.domain = 'stf.jus.br'
        self.start_urls = [
            'http://www.stf.jus.br/portal/jurisprudencia/listarJurisprudencia.asp?'+
            's1=%28%40JULG+%3E%3D+'+
             iDate +                 
            '%29%28%40JULG+%3C%3D+'+
             fDate +
            '%29'+
            '&pagina=1'+
            '&base=baseAcordaos'
        ]

    def parse( self, response ):
        print "\n\n\n\n"
    	sel = Selector(response)
        body = sel.xpath(
            '/html/body/div[@id="pagina"]'+
            '/div[@id="conteiner"]'+
            '/div[@id="corpo"]'+
            '/div[@class="conteudo"]'+
            '/div[@id="divNaoImprimir"][2]'+
            '/table[1]/tr/td[2]/text()').extract()
        r = re.search(r"([0-9]+)", str(body))
        if r:
            ndocs = str(r.group(0))
        else:
            ndocs = '0'
        with open(FILE_NDOCS, 'w') as f:
            f.write( ndocs)
            f.close() 
        print ndocs + "documentos encontrados\n"
