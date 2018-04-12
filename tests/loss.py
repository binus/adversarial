#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Script for performing loss study."""

# Basic import(s)
import os
import glob
import json
import itertools

# Set Keras backend
os.environ['KERAS_BACKEND'] = 'tensorflow'

# Scientific import(s)
import ROOT
import numpy as np
import root_numpy
import matplotlib.pyplot as plt

# Project import(s)
from adversarial.utils import parse_args, initialise, mkdir
from adversarial.layers import PosteriorLayer
from adversarial.profile import profile, Profile
from adversarial.constants import *
from .studies.common import *

# Custom import(s)
import rootplotting as rp


# Main function definition
@profile
def main (args):

    # Initialising
    # --------------------------------------------------------------------------
    args, cfg = initialise(args)


    # Common definitions
    # --------------------------------------------------------------------------
    experiment  = 'classifier'
    num_folds   = 3
    lambda_reg  = 0.1 # 10


    # Perform classifier CV study
    # --------------------------------------------------------------------------
    paths = sorted(glob.glob('models/adversarial/classifier/crossval/history__crossval_{}__*of{}.json'.format(experiment, num_folds)))

    if len(paths) == 0:
        print "No models found for classifier CV study."
    else:
        with Profile("Study: Classifier CV loss"):

            # Read losses from files
            losses = {'train': list(), 'val': list()}
            for path in paths:
                with open(path, 'r') as f:
                    d = json.load(f)
                    pass

                loss = np.array(d['val_loss'])
                losses['val'].append(loss)
                loss = np.array(d['loss'])
                losses['train'].append(loss)
                pass

            # Define variable(s)
            bins     = np.arange(len(loss))
            histbins = np.arange(len(loss) + 1) + 0.5
            
            # Canvas
            c = rp.canvas(batch=True)

            # Plots
            categories = list()

            # -- Validation
            loss_mean = np.mean(losses['val'], axis=0)
            loss_std  = np.std (losses['val'], axis=0)
            hist = ROOT.TH1F('val_loss', "", len(histbins) - 1, histbins)
            for idx in range(len(loss_mean)):
                hist.SetBinContent(idx + 1, loss_mean[idx])
                hist.SetBinError  (idx + 1, loss_std [idx])
                pass

            c.hist([0], bins=[0, max(bins)], linewidth=0, linestyle=0)  # Force correct x-axis
            c.hist(hist, fillcolor=rp.colours[5], alpha=0.3, option='LE3')
            c.hist(hist, linecolor=rp.colours[5], linewidth=3, option='HISTL')

            categories += [('Validation',  # (CV avg. #pm RMS)',
                            {'linestyle': 1, 'linewidth': 3,
                             'linecolor': rp.colours[5], 'fillcolor': rp.colours[5],
                             'alpha': 0.3,  'option': 'FL'})]

            # -- Training
            loss_mean = np.mean(losses['train'], axis=0)
            loss_std  = np.std (losses['train'], axis=0)
            hist = ROOT.TH1F('loss', "", len(histbins) - 1, histbins)
            for idx in range(len(loss_mean)):
                hist.SetBinContent(idx + 1, loss_mean[idx])
                hist.SetBinError  (idx + 1, loss_std [idx])
                pass

            c.hist(hist, fillcolor=rp.colours[1], alpha=0.3, option='LE3')
            c.hist(hist, linecolor=rp.colours[1], linewidth=3, linestyle=2, option='HISTL')

            categories += [('Training',  #    (CV avg. #pm RMS)',
                            {'linestyle': 2, 'linewidth': 3,
                             'linecolor': rp.colours[1], 'fillcolor': rp.colours[1],
                             'alpha': 0.3,  'option': 'FL'})]

            # Decorations
            c.pads()[0]._yaxis().SetNdivisions(505)
            c.xlabel("Training epoch")
            c.ylabel("Cross-validation classifier loss, L_{clf}")
            c.xlim(0, max(bins))
            c.ylim(0.3, 0.5)
            c.legend(categories=categories, width=0.25)  # ..., xmin=0.475
            c.text(TEXT + ["#it{W} jet tagging", "Neural network (NN) classifier"],
                   qualifier=QUALIFIER)
            # Save
            mkdir('figures/')
            c.save('figures/loss_{}.pdf'.format(experiment))
            pass
        pass


    # Compute entropy if decorrelation prior
    # --------------------------------------------------------------------------


    """
    # Computing differential entropy of distribution
    from adversarial.new_utils import load_data
    data, features, _ = load_data('data/data.h5')

    print "signal, background = {}, {}".format(np.sum(data['signal'] == 1), np.sum(data['signal'] == 0))
    data = data[data['train']  == 1]  # @TEMP
    data = data[data['signal'] == 0]

    from run.reweight.common import get_input as reweighter_input
    from run.reweight.common import Scenario as ReweightedScenario
    decorrelation, weight_decorrelation = reweighter_input(data, ReweightedScenario.FLATNESS)

    # Flatness reweighting
    import gzip, pickle
    from run.reweight.common import Scenario, get_input

    with gzip.open('models/reweight/reweighter_flatness.pkl.gz', 'r') as f:
        reweighter = pickle.load(f)
        pass

    weight_flatness  = reweighter.predict_weights(decorrelation, original_weight=weight_decorrelation)
    weight_flatness *= np.sum(data['weight']) / np.sum(weight_flatness)

    weight_decorrelation /= weight_decorrelation.mean()  # Normalise to <w> = 1

    # Plot priors
    xmin, xmax = decorrelation.min(), decorrelation.max()
    nbins = 100
    bins = np.linspace(xmin, xmax, nbins + 1, endpoint=True)


    c = rp.canvas(batch=True)
    hist_normal   = c.hist(decorrelation[:,0], bins=bins, weights=weight_decorrelation, display=False)
    hist_flatness = c.hist(decorrelation[:,0], bins=bins, weights=weight_flatness,      display=False)

    # -- Normalise
    int_normal   = float(hist_normal  .Integral())
    int_flatness = float(hist_flatness.Integral())
    for ibin in range(1, nbins + 1):
        bin_width = float(hist_normal.GetBinWidth(ibin))
        hist_normal  .SetBinContent(ibin, hist_normal  .GetBinContent(ibin) / int_normal   / bin_width)
        hist_flatness.SetBinContent(ibin, hist_flatness.GetBinContent(ibin) / int_flatness / bin_width)
        pass

    sigma = 0.15
    bincentres = bins[:-1] + np.diff(bins) * 0.5
    prior_gaus = 1. / np.sqrt(2. * np.pi * np.square(sigma)) * np.exp(- np.square(bincentres - .5) / 2. / np.square(sigma))

    # Compute differential entropy of distributions
    prior_normal   = root_numpy.hist2array(hist_normal)
    prior_flatness = root_numpy.hist2array(hist_flatness)
    H_normal   = - np.sum(prior_normal   * np.log(prior_normal)   * bin_width)
    H_flatness = - np.sum(prior_flatness * np.log(prior_flatness) * bin_width)
    H_gaus     = - np.sum(prior_gaus     * np.log(prior_gaus)     * bin_width)


    # Robustly estimate the entropy of the prior
    num_bins = 50
    H_mean = entropy(decorrelation[:,0], num_bins=num_bins, weights=weight_decorrelation)
    H_err_syst = max(abs(H_mean - entropy(decorrelation[:,0], num_bins=num_bins // 2, weights=weight_decorrelation)),
                     abs(H_mean - entropy(decorrelation[:,0], num_bins=num_bins *  2, weights=weight_decorrelation)))
    H_bootstrap = list()
    N = decorrelation.shape[0]
    for _ in range(10):
        indices = np.random.choice(N,N,replace=True)
        H_bootstrap.append(entropy(decorrelation[indices,0], num_bins=num_bins, weights=weight_decorrelation[indices]))
        pass
    H_err_stat = np.std(H_bootstrap)

    print "Entropy of prior: {:7.4f} ± {:6.4f} (stat.) ± {:6.4f} (syst)".format(H_mean, H_err_stat, H_err_syst)

    print "H_normal:   {:7.4f} ({:6.4f})"     .format(H_normal,   np.sum(prior_normal   * bin_width))
    print "H_flatness: {:7.4f} ({:6.4f} / {:7.4f})".format(H_flatness, np.sum(prior_flatness * bin_width), np.log(xmax - xmin))
    print "H_gaus:     {:7.4f} ({:6.4f} / {:7.4f})".format(H_gaus,     np.sum(prior_gaus     * bin_width), np.log(sigma * np.sqrt(2. * np.pi * np.e)))
    #"""

    #P_X_factorised = list()
    #cols = [np.array(col) for col in X.T.tolist()]


    #return

    # ...

    #print "X.shape:", P_X.shape


    #H_XY =
    #H_X =
    #H_Y_given_X = H_XY - HX


    """
    # Posteriors
    PL1 = PosteriorLayer(1,1)
    PL2 = PosteriorLayer(2,1)

    x = bincentres.flatten().reshape(-1,1)
    ones = np.ones_like(x)

    import tensorflow as tf
    sess = tf.InteractiveSession()

    coeffs =  ones
    means  = [ones * 0.50]
    widths = [ones * 10.]
    input1 = [tf.constant(coeffs)] + \
             [tf.constant(mean)  for mean  in means]  + \
             [tf.constant(width) for width in widths] + \
             [tf.constant(x)]

    coeffs =  np.hstack((ones * 0.40, ones * 0.60))
    means  = [np.hstack((ones * 0.25, ones * 0.65))]
    widths = [np.hstack((ones * 0.10, ones * 0.25))]
    input2 = [tf.constant(coeffs)] + \
             [tf.constant(mean)  for mean  in means]  + \
             [tf.constant(width) for width in widths] + \
             [tf.constant(x)]

    print "input1:", input1
    print "input2:", input2

    post1 = PL1.call(input1).eval()
    post2 = PL2.call(input2).eval()

    print "post1.shape:", post1.shape
    """

    """
    num_trials = 10
    num_sample = 10000
    print "Sampling KL loss on prior ({} x {}).".format(num_trials, num_sample)
    prior_losses = list()

    for _ in range(num_trials):
        sample = np.random.choice(bincentres, num_sample, p=prior_normal / np.sum(prior_normal))

        indices = np.argmin(np.abs(bincentres - np.repeat(sample.reshape((-1,1)), len(bincentres), axis=1)), axis=1)
        probs = prior_normal[indices]
        prior_losses.append(np.mean(-np.log(probs)))
        pass
    print "Avg. loss for prior: {:7.4f} ± {:6.4f}".format(np.mean(prior_losses), np.std(prior_losses))


    c.hist(hist_normal,   linecolor=rp.colours[0], label='normal')
    c.hist(hist_flatness, linecolor=rp.colours[1], label='flatness')
    c.hist(prior_gaus,    bins=bins,  linecolor=rp.colours[2], label='gauss')
    #### c.hist(post1,         bins=bins,  linecolor=rp.colours[4], linestyle=2, label='post1', option='HISTL')
    #### c.hist(post2,         bins=bins,  linecolor=rp.colours[3], linestyle=2, label='post2', option='HISTL')
    c.legend()
    c.save('figures/tmp_prior.pdf')
    """


    #return


    # Perform adversarial loss study
    # --------------------------------------------------------------------------
    #### for lambda_reg in [0.1, 0.3, 1, 3, 10, 30, 100]:
    ####     plot_adversarial_training_loss(lambda_reg, 5, 20, H_normal)
    ####     pass

    return 0  # @TEMP

    basedir='models/adversarial/combined/full/'
    H_normal = -0.47
    for lambda_reg in [3, 10, 30, 100]:
        plot_adversarial_training_loss(lambda_reg, None, 20, H_normal, basedir=basedir)
        pass

    return 0


@profile
def plot_adversarial_training_loss (lambda_reg, num_folds, pretrain_epochs, H_prior=None, basedir='models/adversarial/combined/crossval/'):
    """
    Plot the classifier, adversary, and combined losses for the adversarial
    training of the jet classifier.
    """

    # Check(s)
    if not basedir.endswith('/'):
        basedir += '/'
        pass

    # Define variable(s)
    digits = int(np.ceil(max(-np.log10(lambda_reg), 0)))
    lambda_str = '{l:.{d:d}f}'.format(d=digits,l=lambda_reg).replace('.', 'p')

    # Get paths to all cross-validation adversarially trained classifiers
    if num_folds:
        paths = sorted(glob.glob(basedir + 'history__combined_lambda{}_*of{}.json'.format(lambda_str, num_folds)))
    else:
        paths = glob.glob(basedir + 'history__combined_lambda{}.json'.format(lambda_str))
        pass

    print "Found {} paths.".format(len(paths))
    if len(paths) == 0:
        return

    keys = ['train_comb', 'train_clf', 'train_adv', 'val_comb', 'val_clf', 'val_adv']
    losses = {key: list() for key in keys}
    for path in paths:
        with open(path, 'r') as f:
            d = json.load(f)
            pass

        # Training
        loss = np.array(d['classifier_loss'])
        losses['train_clf'].append(loss)
        loss = np.array(d['adversary_loss'])
        losses['train_adv'].append(loss)
        losses['train_comb'].append(losses['train_clf'][-1] - lambda_reg * losses['train_adv'][-1])

        # Validation
        loss = np.array(d['val_classifier_loss'])
        losses['val_clf'].append(loss)
        loss = np.array(d['val_adversary_loss'])
        losses['val_adv'].append(loss)
        losses['val_comb'].append(losses['val_clf'][-1] - lambda_reg * losses['val_adv'][-1])
        pass


    # Plot results
    c = rp.canvas(batch=True, num_pads=3, ratio=False, size=(600,800))
    bins     = np.arange(len(loss))
    histbins = np.arange(len(loss) + 1) - 0.5

    # Axes
    for idx in range(3):
        c.pads()[idx].hist([0], bins=[0,len(bins) - 1], linewidth=0, linestyle=0)  # Force correct x-axis
        pass

    # Plots
    categories = list()
    for ityp, typ in enumerate(['val', 'train']):
        for igrp, grp in enumerate(['clf', 'adv', 'comb']):
            key = '{}_{}'.format(typ,grp)
            colour = rp.colours[1 if typ == 'train' else 5]

            # Create histogram
            loss_mean = np.mean(losses[key], axis=0)
            loss_std  = np.std (losses[key], axis=0)
            hist = ROOT.TH1F(key, "", len(histbins) - 1, histbins)
            for ibin in range(len(loss_mean)):
                hist.SetBinContent(ibin + 1, loss_mean[ibin])
                hist.SetBinError  (ibin + 1, loss_std [ibin])
                pass

            c.pads()[igrp].hist(hist, fillcolor=colour, linestyle=ityp + 1, linewidth=0, alpha=0.3, option='LE3')
            c.pads()[igrp].hist(hist, fillcolor=0,     fillstyle=0,         linecolor=colour, linestyle=ityp + 1, linewidth=3,            option='HISTL')


            if igrp == 0:
                categories += [('Training' if typ == 'train' else 'Validation',
                                {'linestyle': ityp + 1, 'linewidth': 3,
                                 'fillcolor': colour, 'alpha': 0.3,
                                 'linecolor': colour, 'option': 'FL'})]
                pass
            pass
        pass

    # Formatting pads
    margin = 0.2
    ymins, ymaxs = list(), list()
    for ipad, pad in enumerate(c.pads()):
        tpad = pad._bare()  # ROOT.TPad
        f = ipad / float(len(c.pads()) - 1)
        tpad.SetLeftMargin(0.20)
        tpad.SetBottomMargin(f * margin)
        tpad.SetTopMargin((1 - f) * margin)
        pad._yaxis().SetNdivisions(505)
        if ipad < len(c.pads()) - 1:  # Not bottom pad
            pad._xaxis().SetLabelOffset(9999.)
            pad._xaxis().SetTitleOffset(9999.)
        else:
            pad._xaxis().SetTitleOffset(3.5)
            pass

        def get_max (h):
            ymax = - np.inf
            for ibin in range(h.GetXaxis().GetNbins()):
                y = h.GetBinContent(ibin + 1)  # + h.GetBinError(ibin + 1)
                if y == 0: continue
                ymax = max(ymax, y)
                pass
            return ymax

        def get_min (h):
            ymin = np.inf
            for ibin in range(h.GetXaxis().GetNbins()):
                y = h.GetBinContent(ibin + 1)  # - h.GetBinError(ibin + 1)
                if y == 0: continue
                ymin = min(ymin, y)
                pass
            return ymin


        ymin, ymax = list(), list()
        for hist in pad._primitives:
            if not isinstance(hist, ROOT.TGraph):
                ymin.append(get_min(hist))
                ymax.append(get_max(hist))
                pass
            pass

        ymin = min(ymin)
        ymax = max(ymax)

        ydiff = ymax - ymin
        ymin -= ydiff * 0.2
        ymax += ydiff * (0.7 if ipad == 0 else (0.7 if ipad == 1 else 0.2))

        pad.ylim(ymin, ymax)

        ymins.append(ymin)
        ymaxs.append(ymax)
        pass

    c._bare().Update()

    # Pre-training boxes
    boxes = list()
    for ipad, pad in enumerate(c.pads()):
        pad._bare().cd()
        boxes.append(ROOT.TBox(0, ymins[ipad], pretrain_epochs, ymaxs[ipad]))
        boxes[-1].SetFillColorAlpha(ROOT.kBlack, 0.05)
        boxes[-1].Draw("SAME")
        pass

    # Vertical lines
    for ipad in range(len(c.pads())):
        align = 'TL' if ipad < 2 else 'BL'
        c.pads()[ipad].xline(pretrain_epochs,
                             ymin=ymins[ipad], ymax=ymaxs[ipad],
                             text='Adversary pre-training  ' if ipad == 0 else None,
                             text_align=align, linestyle=1, linecolor=ROOT.kGray + 2)
        pass

    # Horizontal lines
    clf_opt_val = c.pads()[0]._primitives[1].GetBinContent(1)
    clf_opt_err = c.pads()[0]._primitives[1].GetBinError  (1)
    c.pads()[0].yline(clf_opt_val)
    if H_prior is not None:
        c.pads()[1].yline(H_prior)
        c.pads()[2].yline(clf_opt_val - lambda_reg * (H_prior))
        pass

    opts = dict(align=31, textcolor=ROOT.kGray + 2, textsize=14)
    c.pads()[0].latex("Standalone NN  ", bins[-1] * 0.98, clf_opt_val                           + (ymaxs[0] - ymins[0]) * 0.03, **opts)

    if H_prior is not None:
        c.pads()[1].latex("#it{H}(prior)  ", bins[-1] * 0.98, H_prior                              + (ymaxs[1] - ymins[1]) * 0.03, **opts)
        opts['align'] = 33
        c.pads()[2].latex("Ideal  ",       bins[-1] * 0.98, clf_opt_val - lambda_reg * (H_prior) - (ymaxs[2] - ymins[2]) * 0.03, **opts)
        pass

    # Decorations
    ROOT.gStyle.SetTitleOffset(2.0, 'y')  # 2.2
    c.xlabel("Training epoch")
    c.pads()[0].ylabel("#it{L}_{clf.}")
    c.pads()[1].ylabel("#it{L}_{adv.}")
    c.pads()[2].ylabel("#it{L}_{clf.} #minus #lambda #it{L}_{adv.}")
    for pad in c.pads():
        pad.xlim(0, max(bins) - 1)
        pass

    c.pads()[0].text([], xmin=0.2, ymax=0.85, qualifier=QUALIFIER)

    c.pads()[1].text(["#sqrt{s} = 13 TeV",
                      "Baseline selection",
                      "Adversarial training (#lambda=%s)" % (lambda_str.replace('p', '.'))
                      ], ATLAS=False, ymax=0.70, xmin=0.35)
    c.pads()[0].legend(xmin=0.60, ymax=0.70, categories=categories)

    # Save
    mkdir('figures/')
    c.save('figures/loss_adversarial_lambda{}_{}.pdf'.format(lambda_str, 'full' if num_folds is None else 'cv'))
    return


def entropy (data, num_bins=None, weights=None):
    """
    ...
    """

    # Define variable(s)
    eps = np.finfo(np.float).eps

    # Check(s)
    if len(data.shape) == 1:
        data = data.reshape((-1,1))
        pass
    assert len(data.shape) == 2, "Didn't understand shape {}".format(data.shape)
    if weights is not None:
        assert weights.size == weights.shape[0], "Please specify one weight per sample. Received array with shape {}".format(weights.shape)
        assert weights.size == data.shape[0],    "Please specify one weight per sample. Received arrasy with shapes {} and {}".format(weights.shape, data.shape)
    else:
        weights = np.ones((data.shape[0],))
        pass

    # Create p.d.f.
    N, dims = data.shape
    num_bins = num_bins if num_bins else int(30 / np.sqrt(dims))
    shape = (num_bins,) * dims
    pdf = np.zeros(shape)
    dX  = np.zeros((num_bins, dims))
    vol = np.ones (shape)
    bins = list()

    # (nBins x nBins x ... x nBins)  -- N times
    # vol[i,j,...,p,q] = dx[0][i] x d[1][j]
    for dim in range(dims):

        # Get data column
        x = data[:,dim]

        # Define bins for current axis dimension
        bins.append(np.linspace(x.min(), x.max(), num_bins + 1, endpoint=True))

        dX[:,dim] = np.diff(bins[-1])
        pass

    pdf, edges = np.histogramdd(data, bins=bins, weights=weights)

    # Compute volume elements
    for indices in itertools.product(*map(range, shape)):
        vol[indices] = np.product([dx[i] for dx,i in zip(dX.T,indices)])
        pass

    # Normalise p.d.f.
    pdf /= pdf.sum()
    pdf /= vol

    # Return entropy
    return - np.sum(pdf * np.log(pdf + eps) * vol)


# Main function call
if __name__ == '__main__':

    # Parse command-line arguments
    args = parse_args()

    # Call main function
    main(args)
    pass
