#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Script for performing study partB -- simple study:roc, jetmass, and some intutive information. """
"""from `output`/study_xxx.h5 to `output`/figures/XXX"""


# Basic import(s)
import re
import gc
import gzip
import itertools

# Get ROOT to stop hogging the command-line options
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

# Scientific import(s)
import numpy as np
import pandas as pd
import pickle
import root_numpy
from array import array
from scipy.stats import entropy
from sklearn.metrics import roc_curve, roc_auc_score

# Project import(s)
from adversarial.utils import initialise, initialise_backend, parse_args, load_data, mkdir, wpercentile, latex,INPUT_DEFAULTS
from adversarial.profile import profile, Profile
from adversarial.constants import *
from run.adversarial.common import initialise_config
from .studies.common import *
import studies
import os
import logging as log

# Custom import(s)
# import rootplotting as rp

#now all keep 4 test and addition samplesexame(), all without weight!
# Main function definition
@profile
def main (args):

    # Initialise
    args, _ = initialise(args,simple=True)

    # Initialise Keras backend
    # initialise_backend(args)

    # Neural network-specific initialisation of the configuration dict
    # initialise_config(args, cfg) #need to keep because cfg is modified here!
    # log.basicConfig(format="%(levelname)s: %(message)s",
    #                 level=log.DEBUG if args.debug else
    #                 log.INFO if args.verbose else
    #                 log.WARNING)


    # Keras import(s)
    # import keras.backend as K
    # from keras.models import load_model

    # Project import(s)
    # from adversarial.models import classifier_model, adversary_model, combined_model, decorrelation_model

    # # Common definitions
    # # --------------------------------------------------------------------------
    # # # -- k-nearest neighbour
    # # kNN_var = 'D2-k#minusNN'
    #
    # # common useful function
    # def meaningful_digits(number):
    #     digits = 0
    #     if number > 0:
    #         digits = int(np.ceil(max(-np.log10(number), 0)))
    #         pass
    #     return '{l:.{d:d}f}'.format(d=digits, l=number)
    #
    # # --------------------------------------------------------------------------
    #
    # # -- Adversarial neural network (ANN) scan
    # lambda_reg = 10.  # should be same with config?
    # # lambda_regs = sorted([1., 3., 10.,100.]) #Allen use 100, but how about train config.jso setting??
    # lambda_regs = sorted([10.])
    # ann_vars = list()
    # lambda_strs = list()
    # for lambda_reg_ in lambda_regs:
    #     lambda_str = meaningful_digits(lambda_reg_).replace('.', 'p')
    #     lambda_strs.append(lambda_str)
    #
    #     ann_var_ = "ANN(#lambda={:s})".format(lambda_str.replace('p', '.'))
    #     ann_vars.append(ann_var_)
    #     pass
    #
    # ann_var = ann_vars[lambda_regs.index(lambda_reg)]
    # if args.debug or True:
    #     ann_vars = [ann_var]
    #
    # # # -- uBoost scan
    #
    # # uboost_eff = 92
    # # uboost_ur  = 0.3
    # # uboost_urs = sorted([0., 0.01, 0.1, 0.3, 1.0])
    # # uboost_var  =  'uBoost(#alpha={:s})'.format(meaningful_digits(uboost_ur))
    # # uboost_vars = ['uBoost(#alpha={:s})'.format(meaningful_digits(ur)) for ur in uboost_urs]
    # # uboost_pattern = 'uboost_ur_{{:4.2f}}_te_{:.0f}_rel21_fixed'.format(uboost_eff)
    #
    # # -- MV2c10 tagger => only 2 b jets!
    # # mv_vars=["sjetVRGT1_MV2c10_discriminant",
    # #          "sjetVRGT2_MV2c10_discriminant"]
    # mv_vars = ["sjetVR1_MV2c10_discriminant",
    #            "sjetVR2_MV2c10_discriminant"]
    # mv_var = "MV2c10"
    #
    # # -- HbbScore tagger
    # sc_vars = ["fjet_HbbScore", "fjet_XbbScoreHiggs", "fjet_XbbScoreTop", "fjet_XbbScoreQCD", "fjet_JSSTopScore"]
    # sc_var = sc_vars[1]
    # sc_var2 = "Higgs/QCD"
    # sc_var3 = sc_vars[0]
    #
    # # -- Truth information (for backup)
    # tru_vars = ["fjet_GhostBHadronsFinalCount", "fjet_GhostCHadronsFinalCount", "fjet_GhostTQuarksFinalCount",
    #             "fjet_GhostHBosonsCount", "fjet_GhostWBosonsCount", "fjet_GhostZBosonsCount",
    #             "sjetVR1_GhostBHadronsFinalCount", "sjetVR1_GhostCHadronsFinalCount",
    #             "sjetVR2_GhostBHadronsFinalCount", "sjetVR2_GhostCHadronsFinalCount",
    #             "sjetVR3_GhostBHadronsFinalCount", "sjetVR3_GhostCHadronsFinalCount",
    #             "sjetVRGT1_GhostBHadronsFinalCount", "sjetVRGT1_GhostCHadronsFinalCount",
    #             "sjetVRGT2_GhostBHadronsFinalCount", "sjetVRGT2_GhostCHadronsFinalCount",
    #             "sjetVRGT3_GhostBHadronsFinalCount", "sjetVRGT3_GhostCHadronsFinalCount", ]
    #
    # # -- Flag indormation
    # flag_vars = ["signal", "train"]
    #
    # # Tagger feature collection
    # # tagger_features = ['Tau21','Tau21DDT', 'D2', kNN_var, 'D2', 'D2CSS', 'NN', ann_var, 'Adaboost', uboost_var]
    # # tagger_features = ['NN', ann_var,mv_var,ann_var,sc_var, ann_var]
    # tagger_features = ['NN', ann_var, mv_var, sc_var]
    import json
    studyConfig="{}/study_{}.json".format(args.output,args.note)
    if os.path.exists(studyConfig):
        with open(studyConfig) as json_file:
            tagger_features = json.load(json_file)
    else:
        print "Not found ", studyConfig, "please run study_A first!"
        return -1
    # Load data
    tempFile = "{}/study_{}.h5".format(args.output,args.note)
    if os.path.exists(tempFile):
        # data = pd.read_hdf(tempFile, "dataset")
        data,_,_ = load_data(tempFile, debug=args.debug, study=True, dropna=True)
    else:
        print "Not found ",tempFile,"please run study_A first!"
        return -1

    # print "Now counts OUTPUT NA, dropped"
    # print data.isna().sum()
    # print data.shape
    # # print "All output NA are dropped, INPUT NA are filled"
    # data=data.dropna()  # drop all missing value in all output vars,
    # # note drop: can't get right score/predict!
    # # note: all input var for train are already filled!
    perform_studies (data, args, tagger_features)
    return 0

def perform_studies (data, args, tagger_features, ann_vars=None):
    """
    Method delegating performance studies.
    """
    masscuts  = [True, False]
    #pt_ranges = [None, (200, 500), (500, 1000), (1000, 2000)]
    pt_ranges = [None, (200*GeV, 500*GeV), (500*GeV, 1000*GeV), (1000*GeV, 2000*GeV)]

    # debug>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    os.chdir(args.output)
    if True:
        with Profile("Study: JSD:debug"):
            for pt_range in pt_ranges:
                studies.jsd(data, args, tagger_features, pt_range)
                pass
            pass
    if False:
        with Profile("Study: Robustness：debug"):
            for masscut in masscuts:
                studies.robustness_full(data, args, tagger_features, masscut=masscut)
                pass
            pass
    if True:
        with Profile("Study: Jet mass comparison:debug"):
            for eff in set(range(0,110,5)):
                studies.jetmasscomparison(data, args, tagger_features,eff,True)
                pass
    if True:
        with Profile("Study: Efficiency:debug"):
            for feat in tagger_features:
                studies.efficiency(data, args, feat)
                pass
            pass
    if True:
        with Profile("Study: ROC:debug"):
            for masscut, pt_range in itertools.product(masscuts, pt_ranges):
                studies.roc(data, args, tagger_features, masscut=masscut, pt_range=pt_range)
                pass
            pass
    if True:
        with Profile("Study: Substructure tagger distributions:debug"):
            mass_ranges = np.linspace(50 * GeV, 300 * GeV, 5 + 1, endpoint=True)
            mass_ranges = [None] + zip(mass_ranges[:-1], mass_ranges[1:])
            if args.max>1: #seems no use... should use multiprocess??
                import threading
                threads = []
                TMAX=args.max
                for feat, pt_range, mass_range in itertools.product(tagger_features, pt_ranges, mass_ranges):  # tagger_features
                    if len(threads)>TMAX:
                        print "Now queue is full, pop first..."
                        thread=threads.pop(0)
                        thread.join()
                        pass
                    print "Add thread...",len(threads)
                    threads.append(threading.Thread(target=studies.distribution,
                                                    args=(data, args, feat, pt_range, mass_range)))
                    threads[-1].start()
                    # studies.distribution(data, args, feat, pt_range, mass_range)
                    pass
                for thread in threads:
                    print "Now join threads..."
                    thread.join()
                pass
            else:
                for feat, pt_range, mass_range in itertools.product(tagger_features, pt_ranges, mass_ranges):  # tagger_features
                    studies.distribution(data, args, feat, pt_range, mass_range)
                    pass
                pass
            pass
    if False:
    # Later will finish thish part with different tagger
        with Profile("Study: Summary plot:debug"):
            regex_nn = re.compile('\#lambda=[\d\.]+')
            # regex_ub = re.compile('\#alpha=[\d\.]+')

            # scan_features = {'NN':       map(lambda feat: (feat, regex_nn.search(feat).group(0)), ann_vars),
            #                  'Adaboost': map(lambda feat: (feat, regex_ub.search(feat).group(0)), uboost_vars)
            #                  }
            scan_features = {'NN': map(lambda feat: (feat, regex_nn.search(feat).group(0)), ann_vars),
                             }

            for masscut, pt_range in itertools.product(masscuts, pt_ranges):
                studies.summary(data, args, tagger_features, scan_features, masscut=masscut, pt_range=pt_range)
                pass
            pass
    # debug>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    return


# Main function call
if __name__ == '__main__':

    # Parse command-line arguments
    args = parse_args(backend=True, plots=True)

    # Call main function
    main(args)
    pass
