#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pymongo import MongoClient
from GraphMaker import GraphMaker


def preprocess_query(query_raw):
    query = {}
    if query_raw:
        queryPairs = query_raw.split(",")
        if not queryPairs:
            queryPairs = query_raw
        for pair in queryPairs:
            pairSplit = pair.split(":")
            field = pairSplit[0].strip()
            value = pairSplit[1].strip()
            query[field] = value
    return query


def get_decisions_ids(collections, query):
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DATABASE = os.getenv("MONGO_DATABASE")
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]

    decisions_ids = []
    colls = []
    if collections == "acordaos":
        colls.append(db["acordaos"])
    elif collections == "decisoes_monocraticas":
        colls.append(db["decisoes_monocraticas"])
    elif collections == "decisoes":
        colls.append(db["acordaos"])
        colls.append(db["decisoes_monocraticas"])

    for coll in colls:
        docs = coll.find(query, no_cursor_timeout=True)
        for doc in docs:
            decisions_ids.append(doc["acordaoId"])
            # decisions_ids.append([doc["acordaoId"], doc["observacao"], doc["similaresTexto"]])

    return decisions_ids, colls


def run_page_rank_iteration(query, collections_name):
    decisions_ids, collections = get_decisions_ids(
         collections_name, query
    )

    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DATABASE = os.getenv("MONGO_DATABASE")
    collection_out_iter_name = "_fake_coll"
    graphMaker = GraphMaker(
        MONGO_URI,
        MONGO_DATABASE,
        collections,
        collection_out_iter_name,
    )

    removed_decisions = []
    compute_similars = "S"
    [acordaos, quotes, quotedBy, similars] = graphMaker.buildDicts(
        query, removed_decisions, compute_similars
    )
    [quotes, quotedBy] = graphMaker.removeInvalidAcordaosFromDicts(
        acordaos, quotes, quotedBy
    )
    # faz grafo ficar sem direção
    new_quotes = {}
    for k, vals in quotes.items():
        if k not in new_quotes:
            new_quotes[k] = set(vals)
        elif k not in new_quotes[v]:
            new_quotes[k].update(vals)
        for v in vals:
            if v not in new_quotes:
                new_quotes[v] = set([k])
            elif k not in new_quotes[v]:
                new_quotes[v].update([k])

    return new_quotes


def create_papers_graphs(new_quotes):
    nodes_degrees = [len(v) for k, v in new_quotes.items()]
    df = pd.DataFrame(nodes_degrees, columns=["count"])
    df_counts = df["count"].value_counts().reset_index()
    df_counts = df_counts.rename(columns={"index": "K"})
    df_counts = df_counts.sort_values(by=['K'])
    N = df_counts["count"].sum()
    df_counts["P(K)"] = df_counts["count"].apply(lambda x: x/N)
    df_counts["log P(K)"] = df_counts["P(K)"].apply(lambda x: np.log(x))
    df_counts["log K"] = df_counts["K"].apply(lambda x: np.log(x))
    df_counts["log P(K) / log K"] = - df_counts["log P(K)"] / df_counts["log K"]

    ax = sns.lmplot(data=df_counts[df_counts["K"] > 0], y="log P(K)", x="log K")
    gamma = df_counts[df_counts["log K"] > 0]["log P(K) / log K"].mean()
    red_patch = mpatches.Patch(label=r"$\gamma$: {:.2f}".format(gamma))
    plt.legend(handles=[red_patch])
    plt.show()
    ax.savefig("gamma_value_log.png")

    plt.clf()
    plt.cla()
    plt.close()

    ax = sns.distplot(df_counts["K"], kde=False, norm_hist=True, bins=100)
    ax.set(yscale="log")
    ax.set(ylim=(0.0001, 0.01))
    red_patch = mpatches.Patch(label=r"Mean: {:.2f}".format(np.mean(df[df["count"] > 0]["count"])))
    plt.legend(handles=[red_patch])
    plt.show()
    ax.figure.savefig("graph_node_degrees_hist.png")


if __name__ == '__main__':
    query_raw = ""
    query = preprocess_query(query_raw)
    new_quotes = run_page_rank_iteration(query, "acordaos")
    create_papers_graphs(new_quotes)
