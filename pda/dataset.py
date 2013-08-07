from __future__ import print_function, division
from pda.channel import Channel, load_labels
import sys
import numpy as np
import pandas as pd
from scipy.spatial import distance
from sklearn.cluster import DBSCAN
from sklearn import metrics
import matplotlib.pyplot as plt
from itertools import cycle

"""
Functions for loading an entire data directory into a list of
Channels and then manipulating those datasets.

I'm using the term "dataset" to mean a list of Channels.
"""

def load_dataset(data_dir='/data/mine/vadeec/jack-merged', ignore_chans=None,
                 only_load_chans=None):
    """Loads an entire dataset directory.

    Args:
        data_dir (str)
        ignore_chans (list of ints or label strings): optional.  
            Don't load these channels.
        only_load_chans (list of ints or label strings): optional.

    Returns:
        list of Channels
    """

    if ignore_chans is not None:
        assert(isinstance(ignore_chans, list))

    channels = []
    labels = load_labels(data_dir)
    print("Found", len(labels), "entries in labels.dat")
    for chan, label in labels.iteritems():
        if ignore_chans is not None:
            if chan in ignore_chans or label in ignore_chans:
                print("Ignoring chan", chan, label)
                continue

        if only_load_chans is not None:
            if chan not in only_load_chans and label not in only_load_chans:
                print("Ignoring chan", chan, label)
                continue

        print("Attempting to load chan", chan, label, "...", end=" ")
        sys.stdout.flush()
        try:
            channels.append(Channel(data_dir, chan))
        except IOError:
            print("FAILED!")
        else:
            print("success.")

    return channels


def dataset_to_dataframe(dataset):
    d = {}
    for ds in dataset:
        d[ds.name] = ds.series
    return pd.DataFrame(d)


def crop_dataset(dataset, start_date, end_date):
    cropped_dataset = []
    for i in range(len(dataset)):
        c = dataset[i].crop(start_date, end_date)
        if len(c.series.index) > 0 and c.series.values.max() > 0:
            cropped_dataset.append(c)
    return cropped_dataset


def plot_each_channel_activity(ax, dataset):
    df = dataset_to_dataframe(dataset)
    df_minutely = df.resample('T', how='max')
    img = df_minutely.values
    img[np.isnan(img)] = 0

    img = np.divide(img, img.max(axis=0))

    # Manually divide each channel by its max power:
    # for i in range(img.shape[1]):
    #     maximum = img[:,i].max()
    #     if maximum > 3000:
    #         maximum = 3000
    #     img[:,i] = img[:,i] / maximum
    #     img[:,i][img[:,i] > 1] = 1

    img[np.isnan(img)] = 0
    img = np.transpose(img)
    ax.imshow(img, aspect='auto', interpolation='none', origin='lower')
    ax.set_yticklabels(df_minutely.columns)
    ax.set_yticks(np.arange(len(df_minutely.columns)))
    for item in ax.get_yticklabels():
        item.set_fontsize(5)
    return ax


def cluster_appliances_period(dataset, period, ignore_chans=[], plot=False):
    """
    Args:
       dataset (list of pda.channel.Channels)
       period (pd.Period)
       ignore_chans (list of ints)

    Returns:
       list of sets of ints.  Each set stores the channel.chan (int)
           of each channel in that set.
    
    Relevant docs:
    http://scikit-learn.org/stable/auto_examples/cluster/plot_dbscan.html
    """

    merged_events = pd.Series()
    for c in dataset:
        if c.chan in ignore_chans:
            continue
        cropped_c = c.crop(period.start_time, period.end_time)
        events = cropped_c.on_off_events()
        events = events[events == 1] # select turn-on events
        events[:] = c.chan # so we can decipher which chan IDs are in each cluster
        merged_events = merged_events.append(events)

    merged_events = merged_events.sort_index()

    # distance.pdist() requires a 2D array so convert
    # datetimeIndex to a 2D array
    x = merged_events.index.astype(int) / 1E9
    x2d = np.zeros((len(x), 2))
    x2d[:,0] = x

    # Calculate square distance vector
    D = distance.squareform(distance.pdist(x2d))

    # Run cluster algorithm
    # eps is the maximum distance between samples.  In our case,
    # it is in units of seconds.
    db = DBSCAN(eps=60*10, min_samples=2, metric="precomputed").fit(D)
    core_samples = db.core_sample_indices_
    labels = db.labels_

    # Number of clusters in labels, ignoring noise if present.
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

    print('Estimated number of clusters: {:d}'.format(n_clusters_))

    if plot:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    colors = cycle('bgrcmybgrcmybgrcmybgrcmy')
    chans_in_each_cluster = []
    for k, col in zip(set(labels), colors):
        if k == -1:
            # Black used for noise.
            col = 'k'
            markersize = 6
        class_members = [index[0] for index in np.argwhere(labels == k)]
        cluster_core_samples = [index for index in core_samples
                                if labels[index] == k]

        if k != -1:
            chans_in_each_cluster.append(set(merged_events.ix[class_members]))

        if plot:
            for index in class_members:
                plot_x = merged_events.index[index]
                if index in core_samples and k != -1:
                    markersize = 14
                else:
                    markersize = 6

                ax.plot(plot_x, merged_events.ix[index], 'o', markerfacecolor=col,
                        markeredgecolor='k', markersize=markersize)

    if plot:
        plt.show()
        ylim = ax.get_ylim()
        ax.set_ylim( [ylim[0]-1, ylim[1]+1] )
        ax.set_title(str(period))
        ax.set_xlabel('time')
        ax.set_ylabel('channel number')
    return chans_in_each_cluster


def cluster_appliances(dataset, ignore_chans=[], period_range=None):
    if period_range is None:
        period_range = pd.period_range(dataset[0].series.index[0], 
                                       dataset[0].series.index[-1], freq='D')
    
    chans_in_each_cluster = []
    for period in period_range:
        print(period)
        chans_in_each_cluster.extend(cluster_appliances_period(dataset, period, ignore_chans))

    freqs = []
    # now find frequently occurring sets
    for s in chans_in_each_cluster:
        freqs.append((s, chans_in_each_cluster.count(s)))

    # Sort by count; highest count first
    freqs.sort(key=lambda x: x[1], reverse=True)
    return freqs
