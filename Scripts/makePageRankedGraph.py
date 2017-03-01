#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pymongo import MongoClient
from Acordao import Acordao
import sys
from datetime import datetime
from GraphMaker import GraphMaker
from PageRanker import PageRanker

# example of command line command
#makePageRankedGraph DJs acordaos "tribunal: STF, localSigla: SP" STF_SP_PR1 1

dbName = sys.argv[1]
collectionInName = sys.argv[2]
queryRaw = sys.argv[3]
collectionOutName = sys.argv[4]
pageRankMode = sys.argv[5]
query = {}
if queryRaw:
    queryPairs = queryRaw.split(',')
    if not queryPairs:
        queryPairs = queryRaw
    for pair in queryPairs:
        pairSplit = pair.split(':')
        field = pairSplit[0].strip()
        value = pairSplit[1].strip()
        query[field] = value

quotes = {}
quotedBy = {}
similars = {}
acordaos = {} 


def mergeDictsSets(h1, h2):
    # BEGIN PARALLELIZABLE
    for k in h2:
        if k in h1:
            h1[k] = h1[k].union(h2[k])
    # END PARALLELIZABLE
    return h1


try:
    graphMaker = GraphMaker(dbName, collectionInName, collectionOutName)
    pageRanker = PageRanker()
    tini = t1 = datetime.now()
    [acordaos, quotes, quotedBy, similars] = graphMaker.buildDicts(query)
    with open('graphPageRankingLog', 'a') as f:
        f.write( "build dicts time %d\n" % (datetime.now() - t1).seconds)
    #pageRanks = pageRanker.calculatePageRanks( acordaos, quotes, quotedBy, pageRankMode)
    t1 = datetime.now()
    [quotes, quotedBy] = graphMaker.removeInvalidAcordaosFromDicts(acordaos, quotes, quotedBy)
    with open('graphPageRankingLog', 'a') as f:
        f.write("remove invalid acordaos from dicts %d\n" % (datetime.now() - t1).seconds)
    t1 = datetime.now()
    quotesPlusSimilars = mergeDictsSets(quotes, similars)
    quotedByPlusSimilars = mergeDictsSets(quotedBy, similars) 
    with open('graphPageRankingLog', 'a') as f:
        f.write("merge quotes with similars %d\n" % (datetime.now() - t1).seconds)
    t1 = datetime.now()
    pageRanks = pageRanker.calculatePageRanks(acordaos, quotesPlusSimilars, quotedByPlusSimilars, pageRankMode)
    with open('graphPageRankingLog', 'a') as f:
        f.write("calculate page ranks %d\n" % (datetime.now() - t1).seconds)
    t1 = datetime.now()
    graphMaker.insertNodes(acordaos, quotes, quotedBy, similars, pageRanks)
    with open('graphPageRankingLog\n', 'a') as f:
        f.write("insert nodes %d" % (datetime.now() - t1).seconds)
except Exception as e:
    with open('graphPageRankingLog\n', 'a') as f:
        f.write("%d: %s"%( (datetime.now()-tini).seconds, e))
