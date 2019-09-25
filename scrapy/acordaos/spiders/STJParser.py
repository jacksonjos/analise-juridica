# -*- coding: utf-8 -*-

from acordaos.spiders.DecisaoParser import DecisaoParser

# from stf.items import StfLawItem
import re

# import time
from datetime import datetime, timedelta


class STJParser(DecisaoParser):
    def parseId(self, text):
        acId = self.getMatchText(text, r"\s*([^\/]*).*")
        return self.normalizeId(acId.strip())

    def normalizeId(seld, Id):
        normId = re.sub(
            r"(\s+[n][oa][s]?\s+)(?=\w*)", " ", Id.strip(), flags=re.IGNORECASE
        )
        normId = re.sub(r"\s+", " ", normId, flags=re.IGNORECASE)
        return normId.upper().strip()

    def parseUfShort(self, text):
        return self.getMatchText(text, r"[^\/]*\/\s*(..).*").upper().strip()

    def parseRelator(self, text):
        return self.getMatchText(text, r"M[A-Za-z\)\(:.]*\W*([^\(]*).*").upper().strip()

    def parseDataJulgamento(self, text):
        text = text.replace("&nbsp", "").strip()
        dataJulg = datetime(
            int(self.getMatchText(text, r"\d\d\/\d\d\/(\d{4})")),
            int(self.getMatchText(text, r"\d\d\/(\d\d)\/\d{4}")),
            int(self.getMatchText(text, r"(\d\d)\/\d\d\/\d{4}")),
        )
        if dataJulg:
            return dataJulg
        return ""

    def parseDataPublicacao(self, text):
        dataPublic = re.search(r"(\d{2})\/(\d{2})\/(\d{4})", text)
        if dataPublic:
            dataPublic = datetime(
                int(dataPublic.group(3)),
                int(dataPublic.group(2)),
                int(dataPublic.group(1)),
            )
            return dataPublic
        return ""

    def parseOrgaoJulgador(self, text):
        text = text.replace("&nbsp", "").strip()
        match = re.search("Julgador:\s*(.*)\s*", text)
        if match:
            return match.group(1).upper().strip()
        return ""

    def parseAcordaoQuotes(self, sel):
        possQuotes = []
        quotes = []
        linksRaw = sel.xpath("./pre/a/text()").extract()
        links = []
        # joins quotes separated by html format (<br>)
        firstPart = ""
        for i, l in enumerate(linksRaw):
            if re.match(r"^.* n[ao]s?$", l, flags=re.IGNORECASE):
                firstPart = l.strip() + " "
            else:
                link = firstPart + l.strip()
                quotes.append(self.normalizeId(link.upper()))
                firstPart = ""
        otherQuotes = sel.xpath("./pre/text()").extract()
        otherQuotes.append("dummy")
        for line in otherQuotes:
            l = re.split(r"[\n,]", line)
            possQuotes.extend(l)
        for q in possQuotes:
            m = self.getMatchText(q.upper(), r"(?:\s*ST[FJ] - )?\s*([A-Z ]+\d+\/?).*")
            if m and not m.endswith("/"):
                quotes.append(m)
        return quotes

    def parseSimilarAcordaos(self, raw):
        similar = []
        lines = raw.split("\n")
        if len(lines) <= 1:
            return []
        for i in range(0, len(lines)):
            if lines[i].startswith(" "):
                continue
            similarAcordaoId = lines[i].replace(" PROCESSO ELETRÔNICO", "").strip()
            similarAcordaoId = similarAcordaoId.replace(
                " ACÓRDÃO ELETRÔNICO", ""
            ).strip()
            similarAcordaoId = similarAcordaoId.replace("-", " ").strip()
            dataJulg = orgaoJulg = relator = ""
            if len(lines) > i + 1:
                dataJulg = self.getMatchText(
                    lines[i + 1], r".*(?:JULG|ANO)-([\d\-]+).*"
                )
                ufShort = self.getMatchText(lines[i + 1], r".*UF-(\w\w).*")
                orgaoJulg = self.getMatchText(lines[i + 1], r".*TURMA-([\w\d]+).*")
                relator = self.getMatchText(lines[i + 1], r".*M[Ii][Nn][-. ]+([^\.]+)")
                relator = relator.replace(" N", "").strip()
                if not dataJulg and not ufShort and not relator:
                    print("doesn't match")
                    print(lines[i : i + 3])
                    continue
                dataJulg = dataJulg.split("-")
                if len(dataJulg) > 1:
                    dataJulg = datetime(
                        int(dataJulg[2]), int(dataJulg[1]), int(dataJulg[0])
                    )
            similarAcordao = {
                "acordaoId": similarAcordaoId,
                "localSigla": ufShort,
                "dataJulg": dataJulg,
                "relator": relator,
                "orgaoJulg": orgaoJulg,
            }
            similar.append(dict(similarAcordao))
        return similar

    def parseLaws(self, text):
        laws = []
        law = {}
        refs = {}
        lawLines = []
        for l in text:
            l = l.upper()
            if l.startswith("LEG"):
                if lawLines:
                    description = self.parseLawDescription(lawLines[0])
                    if description:
                        lawLines = lawLines[1:]
                        law["descricao"] = description
                    law["refs"] = self.parseLawReferences("".join(lawLines))
                laws.append(law)
                law = {}
                lawLines = []
                law["descricao"] = ""
                law["refs"] = []
                law["sigla"] = self.getMatchText(l, r"\s*LEG[-:]\w+\s+([^\s]+).*")
                law["tipo"] = self.getMatchText(l, r"\s*LEG[-:](\w+).*")
                law["ano"] = self.getMatchText(l, r".*ANO[-:](\d+).*")
            else:
                lawLines.append(" " + l.strip())
        # append last law
        if law:
            if lawLines:
                description = self.parseLawDescription(lawLines[0])
                law["descricao"] = description
                if description:
                    lawLines = lawLines[1:]
            law["refs"] = self.parseLawReferences("".join(lawLines))
            laws.append(law)
        return laws

    def parseSimilarAcordaos(self, similarsRawLst):
        similars = []
        dataJulg = uf = Id = ""
        for s in similarsRawLst:
            match = re.match(r"([\w\s]+\d+)\s+(\w+)\s.*", s)
            if match:
                Id = self.normalizeId(match.group(1).strip())
                uf = match.group(2)
            match = re.search("DECIS\xc3+O:\s*([\d\/]+)", s, flags=re.IGNORECASE)
            if match:
                data = match.group(1)
                data = re.split(r"[\/\-]", data)
                if len(data) > 2:
                    dataJulg = datetime(int(data[2]), int(data[1]), int(data[0]))
            if Id:
                similarAc = {
                    "acordaoId": Id,
                    "localSigla": uf,
                    "dataJulg": dataJulg,
                    "relator": "",
                    "orgaoJulg": "",
                }
                similars.append(dict(similarAc))
        return similars

    def printLaw(self, law):
        print("-------------------------------------------------------------")
        print("sigla: " + law["sigla"])
        print("desc: " + law["descricao"])
        print("tipo: " + law["tipo"])
        print("ano: " + law["ano"])
        print("refs: ")
        #       print(law["refs"]
        for i, a in enumerate(law["refs"]):
            print(a)
        print("-------------------------------------------------------------")
