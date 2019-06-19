import random
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
import torch.utils.data as util_data
from data_list import ImageList
import pre_process as prep

def get_dev_risk(weight, error):
    """
    :param weight: shape [N, 1], the importance weight for N source samples in the validation set
    :param error: shape [N, 1], the error value for each source sample in the validation set
    (typically 0 for correct classification and 1 for wrong classification)
    """
    N, d = weight.shape
    _N, _d = error.shape
    assert N == _N and d == _d, 'dimension mismatch!'
    weighted_error = weight * error # weight correspond to Ntr/Nts, error correspond to (1-M(fv))/M(fv)
    cov = np.cov(np.concatenate((weighted_error, weight), axis=1),rowvar=False)[0][1]
    var_w = np.var(weight, ddof=1)
    eta = - cov / var_w
    return np.mean(weighted_error) + eta * np.mean(weight) - eta


def get_weight(source_feature, target_feature, validation_feature): # 这三个feature根据类别不同，是不一样的. source与target这里需注意一下数据量threshold 2倍的事儿
    """
    :param source_feature: shape [N_tr, d], features from training set
    :param target_feature: shape [N_te, d], features from test set
    :param validation_feature: shape [N_v, d], features from validation set
    :return:
    """
    N_s, d = source_feature.shape  
    N_t, _d = target_feature.shape
    if float(N_s)/N_t > 2:
        source_feature = random_select_src(source_feature, target_feature)
    else:
        source_feature = source_feature.copy()
    target_feature = target_feature.copy()
    all_feature = np.concatenate((source_feature, target_feature))
    all_label = np.asarray([1] * N_s + [0] * N_t,dtype=np.int32) # 1->source 0->target
    feature_for_train,feature_for_test, label_for_train,label_for_test = train_test_split(all_feature, all_label, train_size = 0.8)

    # here is train, test split, concatenating the data from source and target

    decays = [1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5]
    val_acc = []
    domain_classifiers = []
    
    for decay in decays:
        domain_classifier = MLPClassifier(hidden_layer_sizes=(d, d, 2),activation='relu',alpha=decay)
        domain_classifier.fit(feature_for_train, label_for_train)
        output = domain_classifier.predict(feature_for_test)
        acc = np.mean((label_for_test == output).astype(np.float32))
        val_acc.append(acc)
        domain_classifiers.append(domain_classifier)
        print('decay is %s, val acc is %s'%(decay, acc))
        
    index = val_acc.index(max(val_acc))
    
    print('val acc is')
    print(val_acc)

    domain_classifier = domain_classifiers[index]

    domain_out = domain_classifier.predict_proba(validation_feature)
    return domain_out[:,:1] / domain_out[:,1:] * N_s * 1.0 / N_t #(Ntr/Nts)*(1-M(fv))/M(fv)

    # correspond to (Ntr/Nts)*(1-M(fv))/M(fv), M(fv) just indicate whether 0 or 1, meaning from source or target

# added function

# def load_cls_data(source_path, target_path, class_num, resize_size, crop_size, batch_size):
#     """
#     :param source_path: path to source data loader file (training)
#     :param target_path: path to target data loader file (testing)
#     :param class_num: number of classes in the dataset
#     :param resize_size: resize size of the image
#     :param crop_size: crop size of the image
#     :param batch_size: bath size for dataloader
#     :param train_val_split:
#     :return:
#     """
#     source_list = open(source_path).readlines()
#     target_list = open(target_path).readlines()
#     src_cls_list = []
#     tar_cls_list = []
#     train_list = []
#     test_list = []
#     # seperate the class
#     for i in range(class_num):
#         src_cls_list.append([j for j in source_list if int(j.split(" ")[1].replace("\n", "")) == i])
#         tar_cls_list.append([j for j in target_list if int(j.split(" ")[1].replace("\n", "")) == i])
#     prep_dict_source = prep_dict_target = prep.image_train(resize_size=resize_size, crop_size=crop_size)
#     # load different class's image
#     for i in range(class_num):
#         dsets_src = ImageList(src_cls_list[i], transform=prep_dict_source)
#         dset_loaders_src = util_data.DataLoader(dsets_src, batch_size=batch_size, shuffle=True, num_workers=4)
#         dsets_tar = ImageList(tar_cls_list[i], transform=prep_dict_target)
#         dset_loaders_tar = util_data.DataLoader(dsets_tar, batch_size=batch_size, shuffle=True, num_workers=4)
#         iter_src = iter(dset_loaders_src)
#         iter_tar = iter(dset_loaders_tar)
#         train_list.append(iter_src)
#         test_list.append(iter_tar)
#     return train_list, test_list

# def new_get_dev_risk(weight, error, class_num): #这里建议weight和error按照class的顺序来排好处理一些
#     """
#     :param weight: shape [N, 1], the importance weight for N source samples in the validation set
#     :param error: shape [N, 1], the error value for each source sample in the validation set
#     (typically 0 for correct classification and 1 for wrong classification)
#     :param class_num: number of classes in the data set
#     :return:
#     """
#     score = 0
#     for i in range(class_num):
#         #建议此处加入weight[i]=,error[i]=
#         N, d = weight[i].shape #要选取weight中class为i的weight。
#         _N, _d = error[i].shape #要选取error中class为i的weight。
#         assert N == _N and d == _d, 'dimension mismatch!'
#         weighted_error = weight[i] * error[i] # 原先的注释有错误。weight应该是来自get_weight，error应该是validation data分类的错误
#         cov = np.cov(np.concatenate((weighted_error, weight[i]), axis=1),rowvar=False)[0][1]
#         var_w = np.var(weight[i], ddof=1)
#         eta = - cov / var_w
#         score += np.mean(weighted_error) + eta * np.mean(weight[i]) - eta
#     return score

def random_select_src(source_feature, target_feature):
    """
    Select at most 2*Ntr data from source feature randomly
    :param source_feature: shape [N_tr, d], features from training set
    :param target_feature: shape [N_te, d], features from test set
    :return:
    """
    N_s, d = source_feature.shape
    N_t, _d = target_feature.shape
    items = [i for i in range(1, N_s)]
    random_list = random.sample(items, 2 * N_t - 1)
    new_source_feature = source_feature[0].reshape(1, d)
    for i in range(2 * N_t):
        new_source_feature = np.concatenate((new_source_feature, source_feature[random_list[i]].reshape(1, d)))
    return new_source_feature

def predict_loss(y, y_pre): #requires how the loss is calculated for the preduct value and the ground truth value
    """

    :param y:
    :param y_pre:
    :return:
    """
    return abs(y - y_pre)

# def val_split(validation_path):
#     """
#     return the validation data and the ground truth value of the validation data
#     :param validation_path: path to the validation set
#     :return:
#     """
#     validation_list = open(validation_path).readlines()
#     N = len(validation_path)
#     ground_truth = np.zeros(shape=(N))
#     for i in range(N):
#         ground_truth[i] = int(validation_path[i].split(" ")[1].replace("\n", ""))

def cross_validation_loss(feature_network, predict_network, source_path, target_path, val_path, class_num, resize_size, crop_size, batch_size):
    source_list = open(source_path).readlines()
    target_list = open(target_path).readlines()
    validation_list = open(val_path).readlines()
    src_cls_list = []
    tar_cls_list = []
    val_cls_list = []
    cross_val_loss = 0
    # seperate the class
    for i in range(class_num):
        src_cls_list.append([j for j in source_list if int(j.split(" ")[1].replace("\n", "")) == i])
        tar_cls_list.append([j for j in target_list if int(j.split(" ")[1].replace("\n", "")) == i])
        val_cls_list.append([j for j in validation_list if int(j.split(" ")[1].replace("\n", "")) == i])
    prep_dict_val = prep_dict_source = prep_dict_target = prep.image_train(resize_size=resize_size, crop_size=crop_size)
    # load different class's image
    for cls in range(class_num):
        dsets_src = ImageList(src_cls_list[cls], transform=prep_dict_source)
        dset_loaders_src = util_data.DataLoader(dsets_src, batch_size=batch_size, shuffle=True, num_workers=4)

        dsets_tar = ImageList(tar_cls_list[cls], transform=prep_dict_target)
        dset_loaders_tar = util_data.DataLoader(dsets_tar, batch_size=batch_size, shuffle=True, num_workers=4)

        dsets_val = ImageList(val_cls_list[cls], transform=prep_dict_val)
        dset_loaders_val = util_data.DataLoader(dsets_val, batch_size=batch_size, shuffle=True, num_workers=4)

        iter_src = iter(dset_loaders_src)
        src_input, src_labels = iter_src.next()
        src_feature = feature_network(src_input)
        for count_src in range(len(src_cls_list[cls]) - 1):
            src_input, src_labels = iter_src.next()
            src_feature = np.append(src_feature, feature_network(src_input), axis=0)

        iter_tar = iter(dset_loaders_tar)
        tar_input, tar_labels = iter_tar.next()
        tar_feature = feature_network(tar_input)
        for count_tar in range(len(tar_cls_list[cls]) - 1):
            tar_input, tar_labels = iter_tar.next()
            tar_feature = np.append(tar_feature, feature_network(tar_input), axis=0)

        iter_val = iter(dset_loaders_val)
        val_input, val_labels = feature_network(src_input)
        val_feature = feature_network(val_input)
        pre_label = predict_network(val_input)
        for count_val in range(len(val_cls_list[cls]) - 1):
            val_input, val_labels = iter_val.next()
            val_feature = np.append(val_feature, feature_network(val_input), axis=0)
            pre_label = np.append(pre_label, predict_network(val_input))
        true_label = np.full((pre_label.size, 1), cls)
        error = predict_loss(true_label, pre_label)
        weight = get_weight(src_feature, tar_feature, val_feature)
        cross_val_loss = cross_val_loss + get_dev_risk(weight, error)
    return cross_val_loss
