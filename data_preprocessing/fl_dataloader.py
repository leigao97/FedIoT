import argparse
import logging
import os
import sys

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "../")))


def add_args(parser):
    """
    parser : argparse.ArgumentParser
    return a parser added with args required by fit
    """
    # Training settings
    parser.add_argument('--model', type=str, default='vae', metavar='N',
                        help='neural network used in training')

    parser.add_argument('--dataset', type=str, default='UCI_MLR', metavar='N',
                        help='dataset used for training')

    parser.add_argument('--data_dir', type=str, default='./../data/UCI-MLR',
                        help='data directory')

    parser.add_argument('--client_num_in_total', type=int, default=20, metavar='NN',
                        help='number of workers in a distributed cluster')

    parser.add_argument('--client_num_per_round', type=int, default=4, metavar='NN',
                        help='number of workers')

    parser.add_argument('--batch_size', type=int, default=32, metavar='N',
                        help='input batch size for training (default: 64)')

    parser.add_argument('--client_optimizer', type=str, default='adam',
                        help='SGD with momentum; adam')

    parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                        help='learning rate (default: 0.001)')

    parser.add_argument('--wd', help='weight decay parameter;', type=float, default=0.001)

    parser.add_argument('--epochs', type=int, default=50, metavar='EP',
                        help='how many epochs will be trained')

    args = parser.parse_args()
    return args


# read the data from the csv
def load_data(args, train_file_name, test_file_name):
    path_data_train = args.data_dir + "/" + train_file_name
    path_data_test = args.data_dir + "/" + test_file_name
    logging.info(path_data_train)
    logging.info(path_data_test)
    db_train = pd.read_csv(path_data_train)
    db_test = pd.read_csv(path_data_test)
    db_train = (db_train - db_train.mean()) / (db_train.std())
    db_test = (db_test - db_test.mean()) / (db_test.std())
    db_train = np.array(db_train)
    db_test = np.array(db_test)
    db_test[np.isnan(db_test)] = 0
    trainset = db_train
    testset = db_test
    len_train = len(trainset)
    len_test = len(testset)
    correct_ratio = 1 - (0.5*len_train)/len_test
    return len_train, len_test, trainset, testset, correct_ratio


def homo_partition_data(args, process_id, dataset):
    if process_id == 0:  # for centralized training
        return dataset
    else:
        total_num = len(dataset)
        idxs = list(range(total_num))
        batch_idxs = np.array_split(idxs, args.client_num_in_total)
        net_dataidx_map = {i: batch_idxs[i] for i in range(args.client_num_in_total)}
        train_data_local_num_dict = {i: len(batch_idxs[i]) for i in range(args.client_num_in_total)}
    return net_dataidx_map, train_data_local_num_dict


def local_dataloader(args, train_file_name, test_file_name, process_id):
    train_data_local_dict = dict()
    test_data_local_dict = dict()
    train_data_num, test_data_num, train_data_global, test_data_global, correct_ratio = load_data(args, train_file_name, test_file_name)

    dataidx_map_train, train_data_local_num_dict = homo_partition_data(args, process_id, train_data_global)
    dataidx_map_test, test_data_local_num_dict = homo_partition_data(args, process_id, test_data_global)

    # for local train data
    for client_idx in range(args.client_num_in_total):
        data_local_train = train_data_global[dataidx_map_train[client_idx]]
        train_data_local_dict[client_idx] = torch.utils.data.DataLoader(data_local_train, batch_size=args.batch_size,
                                                                        shuffle=False,
                                                                        num_workers=0)
        #logging.info("client_idx = %d, local_train_sample_number = %d" % (client_idx, train_data_local_num_dict[client_idx]))

    # for local test data
    for client_idx in range(args.client_num_in_total):
        data_local_test = test_data_global[dataidx_map_test[client_idx]]
        test_data_local_dict[client_idx] = torch.utils.data.DataLoader(data_local_test, batch_size= 1,
                                                                        shuffle=False,
                                                                        num_workers=0)
        #logging.info("client_idx = %d, local_test_sample_number = %d" % (client_idx, test_data_local_num_dict[client_idx]))

    return train_data_num, test_data_num, train_data_global, test_data_global, \
           train_data_local_num_dict, train_data_local_dict, test_data_local_dict, correct_ratio


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO,
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S')

    # parse python script input parameters
    parser = argparse.ArgumentParser()
    args = add_args(parser)
    logging.info(args)

    dataset = local_dataloader(args,'/Danmini_Doorbell/doorbell_train_norm.csv', '/Danmini_Doorbell/doorbell_test_norm.csv', 1)
    [train_data_num, test_data_num, train_data_global, test_data_global,
     train_data_local_num_dict, train_data_local_dict, test_data_local_dict, correct_ratio] = dataset

