from __future__ import print_function, division
import math
import numpy as np

from bhc import bhc


class rbhc(object):
    """
    An instance of Randomized Bayesian hierarchical clustering CRP 
    mixture model.
    Attributes
    ----------

    Notes
    -----
    The cost of rBHC scales as O(nlogn) and so should be preferred
    for large data sets.
    """

    def __init__(self, data, data_model, crp_alpha=1.0, sub_size=50):

        """
        Init a rbhc instance and perform the clustering.

        Parameters
        ----------
        data : numpy.ndarray (n, d)
            Array of data where each row is a data point and each 
            column is a dimension.
        data_model : CollapsibleDistribution
            Provides the approprite ``log_marginal_likelihood`` 
            function for the data.
        crp_alpha : float (0, Inf)
            CRP concentration parameter.
        sub_size : int
            The size of the random subset of pooints used to form the
            tree whose top split is employed to filter the data.
            Denoted m in the Heller & Ghahramani (2005b).
        """        
        self.data = data
        self.data_model = data_model
        self.crp_alpha = crp_alpha
        self.sub_size = sub_size

        # initialize the tree

        self.assignments = [np.zeros(data.size)]

#        self.nodes = []
        root_node = rbhc_Node(data, data_model, crp_alpha)

#        self.tree = rbhc_Node.recursive_split(root_node, 50)
        self.recursive_split(root_node)



    def recursive_split(self, parent_node):

        rBHC_split, children = rbhc_Node.as_split(parent_node,
                                                  self.sub_size)

        if rBHC_split:      # continue recussing down
           self.recursive_split(children[0])
           self.recursive_split(children[1])

        else:               # terminate
            print("reached the leaves")
        




class rbhc_Node(object):
    """ A node in the randomised Bayesian hierarchical clustering.
        Attributes
        ----------
        nk : int
            Number of data points assigned to the node
        data : numpy.ndarrary (n, d)
            The data assigned to the Node. Each row is a datum.
        data_model : idsteach.CollapsibleDistribution
            The data model used to calcuate marginal likelihoods
        crp_alpha : float
            Chinese restaurant process concentration parameter
    """
    def __init__(self, data, data_model, crp_alpha=1.0):
        """ __init__(data, data_model, crp_alpha=1.0)

            Initialise a rBHC node.

            Parameters
            ----------
            data : numpy.ndarrary (n, d)
                The data assigned to the Node. Each row is a datum.
            data_model : idsteach.CollapsibleDistribution
                The data model used to calcuate marginal likelihoods
            crp_alpha : float, optional
                Chinese restaurant process concentration parameter
        """

        self.data = data
        self.data_model = data_model
        self.crp_alpha = crp_alpha

        self.nk = data.shape[0]


    def set_rk(self, log_rk):
        """ set_rk(log_rk)

            Set the value of the ln(r_k) The probability of the 
            merged hypothesis as given in Eqn 3 of Heller & Ghahramani
            (2005a)

            Parameters
            ----------
            log_rk : float
                The value of log_rk for the node
        """
        self.log_rk = log_rk

    @classmethod
    def as_split(cls, parent_node, sub_size):
        """ as_split(parent_node, subsize)

            Perform a splitting of a rBHC node into two children.
            If the number of data points is large a randomized
            filtered split, as in Fig 4 of Heller & Ghahramani (2005b)
            is performed.
            Otherwise, if the number of points is less than or equal
            to subsize then these are simply subject to a bhc 
            clustering.

            Parameters
            ----------
            parent_node : rbhc_Node
                The parent node that is going to be split
            sub_size : int
                The size of the random subset of pooints used to form
                the tree whose top split is employed to filter the
                data.
                Denoted m in Heller & Ghahramani (2005b).

            Returns
            -------
            rBHC_split : bool
                True if the size of data is greater than sub_size and
                so a rBHC split/filtering has occured.
                False if the size of data is less than/equal to
                sub_size and so an bhc clustering that includes all
                the data has been found.
            children : list(rbhc_Node) , bhc
                A clustering of the data, either onto two child
                rbhc_Nodes or as a full bhc tree of all the data 
                within parent_node.
        """

        print(parent_node.nk)

        if parent_node.nk>sub_size:    # do rBHC filter
            # make subsample tree
            parent_node.subsample_bhc(sub_size)

            # filter data through top level of subsample_bhc
            parent_node.filter_data()

            # create new nodes

            left_child = cls(parent_node.left_data,
                             parent_node.data_model, 
                             parent_node.crp_alpha)
            right_child = cls(parent_node.right_data,
                             parent_node.data_model, 
                             parent_node.crp_alpha)
            rBHC_split = True
            children = [left_child, right_child]

       
        else:               # just use the bhc tree
            children = bhc(parent_node.data, 
                           parent_node.data_model, 
                           parent_node.crp_alpha)
            rBHC_split = False

        return (rBHC_split, children)
        


    def subsample_bhc(self, sub_size):
        """ subsample_bhc(sub_size)

            Produce a subsample of sub_size data points and then
            perform an bhc clustering on it.
        
            Parameters
            ----------
            sub_size : int
                The size of the random subset of pooints used to form
                the tree whose top split is employed to filter the
                data.
                Denoted m in Heller & Ghahramani (2005b).
        """

        self.sub_indexes = np.random.choice(np.arange(self.nk), 
                                            sub_size, replace=False)
        sub_data = self.data[self.sub_indexes]
        self.sub_bhc = bhc(sub_data, self.data_model, self.crp_alpha)

    def filter_data(self):
        """ filter_data()

            Filter the data in a rbhc_node onto the two Nodes at the
            second from top layer of a bhc tree.
        """
            

        self.left_data = self.sub_bhc.root_node.left_child.data
        self.right_data = self.sub_bhc.root_node.right_child.data

        # get non-subset data indices

        notsub_indexes = np.setdiff1d(np.arange(self.nk), 
                                      self.sub_indexes,
                                      assume_unique=True)

        # Run through non-subset data

        for ind in notsub_indexes:
            left_prob = (self.sub_bhc.root_node.left_child.log_pi
                         + self.data_model.log_marginal_likelihood(
                            np.vstack((self.left_data, 
                                            self.data[ind])) ))
            right_prob = (self.sub_bhc.root_node.right_child.log_pi
                         + self.data_model.log_marginal_likelihood(
                            np.vstack((self.right_data, 
                                            self.data[ind])) ))

            if left_prob>=right_prob:
                # possibly change this to make tupe and vstack at 
                # end if cost is high
                self.left_data = np.vstack((self.left_data, 
                                            self.data[ind]))
            else:
                self.right_data = np.vstack((self.right_data, 
                                             self.data[ind]))
        