import math
import os
import sys

import numpy as np
from util import load_result
from itertools import combinations
from itertools import product
from ontology import Ontology


def get_max_tree_distance(ontology, tags, debug=False):
    """
    Description:
        Return max tree distance which can be derived with given tag list.
    Parameters:
        tags: list of tags used in training. (type: list)
              [Example] ['Acoustic guitar', 'Electric Guitar', ..., 'Piano']
    """

    # create combination between tags
    comb = combinations(tags, 2)

    # initiate maximum distance between two tags
    max_dist = 0

    # loop for every combination
    for item in comb:
        # calculate distance between two tags
        distance = ontology.get_min_distance(item[0], item[1])
        if debug:
            print("'%s'-'%s': %d" % (item[0], item[1], distance))

        # update max_dist if distance > max_dist
        max_dist = distance if distance > max_dist else max_dist

    return max_dist


def get_min_tag_distance(ontology, tags_x, tags_y):
    """
    Description:
        Return minimum available tree distance between two videos
    Parameters:
        tags_x: tags of one video                
        tags_y: tags of the other video
                [Example] 
        [Example] tags_x = ['Electric Guitar', 'Human Voice']
                  tags_y = ['Human Voice']
                  This function with the example above should return 0,
                  because 'Human Voice' tag exists in both of tag lists.

                  tags_x = ['Piano', 'Guitar', 'Bass Guitar']
                  tags_y = ['Accordion']
                  This function with the example above should return the
                  distance between 'Accordion' and 'Piano', because its distance
                  will be the smallest among the followings:
                  'Piano' - 'Accordion', 'Guitar' - 'Accordion', 'Bass Guitar' - 'Accordion'
    """
    products = product(tags_x, tags_y)
    min_dist = sys.maxsize
    for x, y in products:
        distance = ontology.get_min_distance(x, y)
        min_dist = min_dist if min_dist < distance else distance

    return min_dist


def dist_to_score(ontology, distances, tags=[], max_dist=-1, debug=False):
    """ 
    Description:
        Convert distances of K retrieved items into scores
    Parameters:
        distances: tree distance between query and K retrieved items
                   [Example] [0, 0, 1, 2, 1, 0, 5, 4, ..., 9] (type: ndarray, len: K)
    [Note] score = max_tree_distance - distance
    """
    # get maximum tree distance
    max_tree_distance = 0
    if max_dist >= 0:
        max_tree_distance = max_dist
    elif len(tags) >= 0:
        max_tree_distance = get_max_tree_distance(ontology, tags)

    scores = max_tree_distance - distances

    return scores


def DCG(scores, k=30, alternate=False):
    """
    Description:
        Return DCG(Discounted Cumulative Gain) with given score (relevance) list
    Parameters:
        scores: score list (type: ndarray, len: N)
              [Example] [8, 6, 6, 8, 4, 7, ..., 2]
        k: length of retrieved items to calculate nDCG
    """
    # return zero if scores is None
    if scores is None or len(scores) < 1:
        return 0.0

    # set the number of items in scores
    scores = scores[:k]
    n_scores = len(scores)

    # use alternative formula of DCG
    if alternate:
        log2i = np.log2(np.asarray(range(1, n_scores + 1)) + 1)
        return ((np.power(2, scores) - 1) / log2i).sum()
    # use traditional formula of DCG
    else:
        log2i = np.log2(np.asarray(range(1, n_scores + 1)) + 1)
        return (scores / log2i).sum()


def IDCG(scores, k=30, alternate=False):
    """
    Description:
        Return IDCG(Ideal Discounted Cumulative Gain) with given score (relevance) list
    Parameters:
        scores: score list (type: ndarray, len: N)
              [Example] [8, 6, 6, 8, 4, 7, ..., 2]
        k: length of retrieved items to calculate nDCG
    """

    if scores is None or len(scores) < 1:
        return 0.0

    # copy and sort scores in incresing order
    s = sorted(scores)
    s = s[::-1][:k]

    # convert s in decresing order
    return DCG(s, k, alternate)


def NDCG(scores, k=30, alternate=False):
    """
    Description:
        Return nDCG(normalized Discounted Cumulative Gain) with given score (relevance) list
    Parameters:
        scores: score list (type: ndarray, len: N)
              [Example] [8, 6, 6, 8, 4, 7, ..., 2]
                
    """
    # return 0 if scores is empty
    if scores is None or len(scores) < 1:
        return 0.0

    # calculate idcg
    idcg = IDCG(scores, k, alternate)
    if idcg == 0:
        return 0.0

    return DCG(scores, k, alternate) / idcg


def do_NDCG(ontology, k, queries, ret_items, tags):
    """
    Description:
        Return Average nDCG for queries and ret_item
    Parameters:
        queries: list of N queries (type: list, dimension: 2D, shape: (N, ?))
              [Example] [[tag1, tag2, ..., tagK], ..., [tagA, tagB, ..., tagG]]
        ret_items: list of N retrieved items (type: list, dimension: 3D, shape: (N, K, ?))
              [Example] [[[tagA, tagB, ..., tagG], ..., [tagX, tagY, ..., tagZ]], ... , [ ... ]]
                
    """
    N = len(queries)
    ndcgs = 0

    # get max_tree_distance
    max_tree_distance = get_max_tree_distance(ontology, tags, debug=False)

    # for every query, calculate nDCG
    for i in range(N):
        distances = np.asarray(
            [get_min_tag_distance(ontology, queries[i], ret_items[i][j]) for j in range(len(ret_items[i]))]
        )
        scores = dist_to_score(ontology, distances, max_dist=max_tree_distance)
        ndcgs += NDCG(scores, k)

    return ndcgs / N


def AP(target, results):
    """
    Description:
        Return AP(Average Precision) with target and results
    Parameters:
        target: list of K retrieved items (type: list, len: K)
              [Example] [tag1, tag2, ..., tagK]
        results: list of N retrieved items (type: list, shape: (N, ?))
              [Example] [[tagA, tagB, ..., tagG], ..., [tagX, tagY, ..., tagZ]]
                
    """
    # initiate variables for average precision
    n = 1  # the number of result
    hit = 0  # the number of hit
    ap = 0  # average precision = 1/hit * sum(precision)

    len_target = len(target)
    for res in results:
        (small_set, big_set) = (target, res) if len_target < len(res) else (res, target)
        for item in small_set:
            if item in big_set:  # hit
                hit += 1
                ap += hit / n
                break
        n += 1

    return ap / hit


def recallAtK(target, results):
    """
    Description:
        Return 'recall at k' with target and results
    Parameters:
        target: list of K retrieved items (type: list, len: K)
              [Example] [tag1, tag2, ..., tagK]
        results: list of N retrieved items (type: list, shape: (N, ?))
              [Example] [[tagA, tagB, ..., tagG], ..., [tagX, tagY, ..., tagZ]]
                
    """
    # initiate variables for average precision
    recall = 0
    K = len(results)

    len_target = len(target)
    for res in results:
        (small_set, big_set) = (target, res) if len_target < len(res) else (res, target)
        for item in small_set:
            if item in big_set:  # hit
                recall += 1
                break

    return recall / K


if __name__ == "__main__":
    data_dir = "json"
    tags = [
        "Acoustic guitar",
        "Bass guitar",
        "Strum",
        "Piano",
        "Independent music",
        "Wedding music",
        "Scary music",
        "Firecracker",
        "Drip",
    ]

    ontology = Ontology(data_dir)
    """
    # Calculate maximum tree distance between tags
    print("Calculate maximum tree distance between tags")
    max_dist = get_max_tree_distance(ontology, tags, debug=False)
    print("Maximum tree distance: ", max_dist, end="\n\n")

    # Convert distances to scores with max_dist
    print("Convert distances to scores with max_dist")
    distances = np.array([0, 0, 1, 2, 1, 0, 5, 4, 8, 9])
    print("Distances: ", distances)
    scores = dist_to_score(ontology, distances, max_dist=max_dist, debug=True)
    print("Scores: ", scores, end="\n\n")

    # Convert distances to scores with tags
    print("Convert distances to scores with tags")
    distances = np.array([0, 0, 1, 2, 1, 0, 5, 4, 8, 9])
    print("Distances: ", distances)
    scores = dist_to_score(ontology, distances, tags=tags, debug=True)
    print("Scores: ", scores, end="\n\n")

    # Do DCG, IDCG, NDCG
    scores = [3, 2, 3, 0, 1, 2]
    print("### Do DCG ###: ", DCG(scores, alternate=False))
    print("### Do IDCG ###: ", IDCG(scores))
    print("### Do NDCG ###: ", NDCG(scores), end="\n\n")

    # Do AP and recall at K
    target = ["a", "b", "c"]
    results = [["a", "g"], ["d", "e", "f", "b"], ["g", "h", "c"], ["y", "k", "p"]]
    print("### AP ###: ", AP(target, results))
    print("### Recall at K ###: ", recallAtK(target, results), end="\n\n")

    # Do get_min_tag_distance: example1
    tags_x = ["Independent music", "Drip"]
    tags_y = ["Drip"]
    print("@@@ get_min_tag_distance1 @@@: ", get_min_tag_distance(ontology, tags_x, tags_y))

    # Do get_min_tag_distance: example2
    tags_x = ["Piano", "Guitar", "Bass guitar"]
    tags_y = ["Accordion"]
    print("@@@ get_min_tag_distance2 @@@: ", get_min_tag_distance(ontology, tags_x, tags_y), end="\n\n")
    """
    # Do average nDCG
    with open("metadata/all_tags.cls") as fi:
        tags = map(lambda x: x[:-1], fi.readlines())
        tags = dict((x, i) for i, x in enumerate(tags))

    file_names = [
        "./results/AVE_aug_ave_i2a.pickle",
        "./results/AVE_aug_ave_a2i.pickle",
        "./results/AVE_aug_ave_i2i.pickle",
        "./results/AVE_aug_ave_a2a.pickle",
    ]

    for f in file_names:
        queries, ret_items = load_result(f)
        ndcgs = do_NDCG(ontology, 5, queries, ret_items, tags)
        print("nDCG: %s" % (f), ndcgs, end="\n\n")
