import glob
import lxml.etree as et
import nltk
import random
import operator
import math
import os
import torch
import errno
# import matplotlib.pyplot as plt
from constants import *
from functools import reduce


def tokenize(start_corpus_path):
    out_path = start_corpus_path[:-4] + "-tokenized.txt"
    if os.path.isfile(out_path):
        print("tokenized file %s already exists" % out_path)
    else:
        tokenized_corpus = open(out_path, "x")
        print("tokenizing ", start_corpus_path)
        for line in open(start_corpus_path):
            tokens = nltk.word_tokenize(line)
            token_line = reduce(lambda s, t: s + " " + t, tokens, "").strip().lower()
            tokenized_corpus.write(token_line + "\n")
        tokenized_corpus.close()


def filter_short_lines(start_corpus_path, n_words):
    temp_file = open(start_corpus_path + "temp", "w")
    for line in open(start_corpus_path):
        if len(line.split()) == n_words:
            temp_file.write(line)
    os.rename(start_corpus_path+"temp", start_corpus_path)


def split(start_corpus_path, train, valid, test):
    train_out = start_corpus_path[:-4] + "-train.txt"
    valid_out = start_corpus_path[:-4] + "-valid.txt"
    test_out = start_corpus_path[:-4] + "-test.txt"
    if os.path.isfile(train_out) or os.path.isfile(valid_out) or os.path.isfile(test_out):
        print("split files for %s already exists" % start_corpus_path)
    elif train + valid + test != 1.0:
        raise Exception("train, valid, and test must sum to 1")
    else:
        train_file = open(train_out, "x")
        valid_file = open(valid_out, "x")
        test_file = open(test_out, "x")
        print("splitting", start_corpus_path)
        for line in open(start_corpus_path):
            n = random.uniform(0, 1)
            if n <= train:
                train_file.write(line)
            elif n <= train + valid:
                valid_file.write(line)
            else:
                test_file.write(line)
        train_file.close()
        valid_file.close()
        test_file.close()


def crop(start_corpus_path, crop_pad_length):
    full_text_file = open(start_corpus_path)
    out_path = start_corpus_path[:-4] + "-crop%d.txt" % crop_pad_length
    if os.path.isfile(out_path):
        print("cropped file %s already exists" % out_path)
    else:
        crop_text_file = open(out_path, "x")
        print("cropping %s to %d words" % (start_corpus_path, crop_pad_length))
        stop_pad = " "
        for _ in range(crop_pad_length):
            stop_pad = stop_pad + STOP + " "
        for line in full_text_file:
            if line is not "\n":
                line = START + " " + line.strip() + stop_pad
                words = line.split(" ")
                words = words[:crop_pad_length]
                line = reduce(lambda s, t: s + " " + t, words) + " " + STOP
                crop_text_file.write(line + "\n")
            else:
                continue


def get_vocab(start_corpus_path, n_vocab=float("inf")):
    counts = {}
    out_path = start_corpus_path[:-4] + "-vocab-" + str(n_vocab) + ".txt"
    if n_vocab is math.inf:
        out_path = start_corpus_path[:-4] + "-vocab-all.txt"
    if os.path.isfile(out_path):
        print("vocab file %s already exists" % out_path)
    else:
        out_file = open(out_path, "x")
        print("getting vocab of size %d for %s" % (n_vocab, start_corpus_path))
        for line in open(start_corpus_path):
            for word in line.split():
                if word in counts:
                    counts[word] = counts[word] + 1
                else:
                    counts[word] = 1
                    if len(counts) % 10000 is 0:
                        print("n_words =", len(counts))
        counts_sorted = sorted(counts.items(), key=operator.itemgetter(1), reverse=True)    # sort vocab by counts
        if n_vocab < len(counts_sorted):
            counts_sorted = counts_sorted[:n_vocab]
        vocab = [x[0] for x in counts_sorted]
        for word in vocab:
            out_file.write(word + "\n")


def unkify(start_corpus_path, vocab):
    out_path = start_corpus_path[:-4] + "-unked-%dwords.txt" % len(vocab)
    if os.path.isfile(out_path):
        print("unked file %s already exists" % out_path)
    else:
        out_file = open(out_path, "x")
        print("unking", start_corpus_path)
        for line in open(start_corpus_path):
            words = line.split()
            for i, word in enumerate(words):
                if word not in vocab:
                    words[i] = UNK
            out_file.write(reduce(lambda s, t: s + " " + t, words).strip() + "\n")
        out_file.close()


def init_embeddings(embeddings_path, vocab, corpus_name, embedding_size):
    #TODO why doesn't generation work when a new embeddings dict is built?
    out_path = embeddings_path[:-4] + "-%s-%dwords.txt" % (corpus_name.split("/")[-3], len(vocab))
    embeddings_dict = dict.fromkeys(list(vocab))
    if os.path.isfile(out_path):
        print("embeddings file %s already exists" % out_path)
    else:
        out_file = open(out_path, "x")
        embeddings_file = open(embeddings_path)
        for line in embeddings_file:
            words = line.split(" ")
            if words[0] in embeddings_dict:
                vec_list = []
                for word in words[1:]:
                    vec_list.append(float(word))
                embeddings_dict[words[0]] = torch.FloatTensor(vec_list)
        for w in vocab:
            if embeddings_dict[w] is None:
                vector = torch.FloatTensor(embedding_size)
                for i in range(embedding_size):
                    vector[i] = random.uniform(-1, 1)
                embeddings_dict[w] = vector
        for k, v in embeddings_dict.items():
            tensor_string = reduce(lambda s1, s2: str(s1) + " " + str(s2), v).strip()
            out_file.write(k + " " + tensor_string + "\n")
        out_file.close()


def read_embeddings(embeddings_path):
    embeddings_dict = {}
    for line in open(embeddings_path):
        words = line.split(" ")
        vec_list = []
        for word in words[1:]:
            vec_list.append(float(word))
        embeddings_dict[words[0]] = torch.FloatTensor(vec_list)
    return embeddings_dict


def apply_xslt(text_paths, xslt_path, data_dir):
    xslt = et.parse(xslt_path)
    transform = et.XSLT(xslt)
    output = open(data_dir + "raw_text", "w")
    for path in text_paths:
        dom = et.parse(path)
        newdom = transform(dom)
        output.write(str(newdom) + "\n")
    # for path in paths:
    #     txt = open(path)
    #     for line in txt:
    #         line = line.strip()
    #         if line is not "":
    #             output.write(line + "\n")
    output.close()















#=============================== MAIN ===============================
raw_corpus = "data/bnc/bnc.txt"
crop_pad_length = 30
n_vocab = 50000





# e_v = embeddings_vocab('embeddings/glove.6B.300d.txt')
# print()

# frequency_counts = get_word_count_counts(raw_corpus)
# line_lengths = get_line_length_counts(raw_corpus)
#
# print(line_lengths)
# plt.plot(list(frequency_counts.keys()),
#          list(frequency_counts.values()))
# plt.show()
# plt.plot([1,2,3], [7, 8, 9])
# plt.show()

# tokenized = tokenize(raw_corpus)
# cropped = crop(tokenized, crop_pad_length)
# vocab = get_vocab(cropped, 20000)
# n_vocab = len(vocab)
# unked = unkify(cropped, vocab)
# filter_short_lines(unked, crop_pad_length+1)
# self.training, self.valid, self.test = dp.split(unked, .85, .05, .10)
# self.embeddings = self.init_embeddings(open(embedding_path))
# bnc =











