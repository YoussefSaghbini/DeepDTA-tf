#!/usr/bin/env python3
# -*- coding:utf-8 -*-
''' 删除第540列，用其他的数据训练，540列预测 '''
import sys
import json
import os
import numpy as np
import pandas as pd
import configparser
import tensorflow as tf

from data_utils import get_now, label_smiles, label_sequence
from model import CNN
from sklearn.metrics import roc_auc_score

os.environ['CUDA_VISIBLE_DEVICES'] = '0'


def main(argv):
    conf = configparser.ConfigParser()
    print(conf.read(argv))
    max_smi_len = conf.getint('model', 'max_smi_len')
    max_seq_len = conf.getint('model', 'max_seq_len')

    data_path = conf.get('model', 'data_path')

    ligands = pd.read_csv(data_path + 'ligands.csv',
                          header=None, names=['id', 'smi'])
    proteins = pd.read_csv(data_path + 'proteins.csv',
                           header=None, names=['id', 'seq'])
    inter = pd.read_csv(data_path + 'inter.csv', header=None)

    other_inter = inter.drop(axis=1, columns=539)

    print(ligands.shape, proteins.shape, inter.shape, other_inter.shape)

    char_smi_set = json.load(open(conf.get('model', 'char_smi')))
    char_seq_set = json.load(open(conf.get('model', 'char_seq')))

    sess = tf.InteractiveSession(
        config=tf.ConfigProto(allow_soft_placement=True))
    model = CNN(filter_num=conf.getint('model', 'filter_num'),
                smi_window_len=conf.getint('model', 'smi_window_len'),
                seq_window_len=conf.getint('model', 'seq_window_len'),
                max_smi_len=max_smi_len,
                max_seq_len=max_seq_len,
                char_smi_set_size=len(char_smi_set),
                char_seq_set_size=len(char_seq_set),
                embed_dim=conf.getint('model', 'embed_dim'))

    trainX, trainy = [], []
    # pos
    pos_inter_row, pos_inter_col = np.where(other_inter == 1)
    pos_coords = list(zip(pos_inter_row, pos_inter_col))

    for row, col in pos_coords:
        smi = ligands.iloc[row, 1]
        seq = proteins.iloc[col, 1]
        try:
            smi_vector = label_smiles(smi, max_smi_len, char_smi_set)
            seq_vector = label_sequence(seq, max_seq_len, char_seq_set)
            trainX.append([smi_vector, seq_vector])
            trainy.append(1)
        except Exception:
            continue
    # neg
    neg_inter_row, neg_inter_col = np.where(other_inter == 0)
    neg_coords = list(zip(neg_inter_row, neg_inter_col))
    np.random.shuffle(neg_coords)
    select = np.random.choice(
        range(len(neg_coords)), size=15 * len(trainX))
    neg_coords = np.asarray(neg_coords)[select]

    for row, col in neg_coords:
        smi = ligands.iloc[row, 1]
        seq = proteins.iloc[col, 1]
        try:
            smi_vector = label_smiles(smi, max_smi_len, char_smi_set)
            seq_vector = label_sequence(seq, max_seq_len, char_seq_set)
            trainX.append([smi_vector, seq_vector])
            trainy.append(0)
        except Exception:
            continue

    trainX = np.asarray(trainX)
    trainy = np.asarray(trainy).reshape([-1, 1])

    print(trainX.shape, trainy.shape)

    pred_seq = proteins.iloc[539, 1]

    predX, predy = [], []
    for i in range(1567):
        smi = ligands.iloc[i, 1]
        try:
            smi_vector = label_smiles(smi, max_smi_len, char_smi_set)
            seq_vector = label_sequence(pred_seq, max_seq_len, char_seq_set)
            predX.append([smi_vector, seq_vector])
            predy.append(inter.iloc[i, 539])
        except Exception:
            continue

    predX = np.asarray(predX)
    print(predX.shape)

    model_path = os.path.join(
        conf.get('model', 'path', fallback='tmp'), 'all.model')
    model.train(sess, trainX, trainy,
                nb_epoch=conf.getint('model', 'num_epoch'),
                batch_size=conf.getint('model', 'batch_size'),
                model_path=model_path)
    res = model.predict(sess, predX, batch_size=conf.getint(
        'model', 'batch_size'), model_path=model_path)
    print('AUC: ', roc_auc_score(predy, res))


if __name__ == "__main__":
    main(sys.argv[1:])