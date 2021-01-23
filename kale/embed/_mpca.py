# =============================================================================
# Author: Shuo Zhou, szhou20@sheffield.ac.uk
#         Haiping Lu, h.lu@sheffield.ac.uk or hplu@ieee.org
# =============================================================================

"""Python implementation of Multilinear Principal Component Analysis (MPCA)

Reference:
    Haiping Lu, K.N. Plataniotis, and A.N. Venetsanopoulos, "MPCA: Multilinear
    Principal Component Analysis of Tensor Objects", IEEE Transactions on Neural
    Networks, Vol. 19, No. 1, Page: 18-39, January 2008. For initial Matlab
    implementation, please go to https://uk.mathworks.com/matlabcentral/fileexchange/26168.
"""
import numpy as np

# import tensorly as tl
from tensorly.base import fold, unfold
from tensorly.tenalg import multi_mode_dot
from sklearn.base import BaseEstimator, TransformerMixin


def _check_ndim(x, n_dim):
    """Raise error if the order/mode of the input data does not
        consistent with the given number of order/mode

    Args:
        x (array-like tensor): input data
        n_dim (int): number of order/mode expected

    """
    if not x.ndim == n_dim:
        raise ValueError("The given data should be %s order tensor but given a %s order tensor"
                         % (n_dim, x.n_dim))


def _check_shape(x, shape_):
    """Raise error if the shape (excluding the last mode) of the input data does not
        consistent with the given shape

    Args:
        x (array-like tensor): input data
        shape_: shape expected

    """
    if not x.shape[1:] == shape_:
        raise ValueError("The expected shape of data is %s, but %s for given data"
                         % (x.shape[1:], shape_))


def _check_dim_shape(x, n_dim, shape_):
    """Check whether the order/mode of the input data is consistent with the given number of mode

    Args:
        x (array-like): input data
        n_dim (int): number of order/mode expected
        shape_: shape expected

    """
    _check_ndim(x, n_dim)
    _check_shape(x, shape_)


class MPCA(BaseEstimator, TransformerMixin):
    """MPCA implementation compatible with sickit-learn

    Args:
        var_ratio (float, optional): Percentage of variance explained
            (between 0 and 1). Defaults to 0.97.
        max_iter (int, optional): Maximum number of iteration. Defaults to 1.
        vectorise (bool): Whether vectorise the transformed tensor. Defaults to False.
        n_components (int): Number of components to keep. Applies only when vectorise=True. 
            Defaults to None.

    Attributes:
        proj_mats (list of array-like): A list of transposed projection matrices, shapes (P_1, I_1), ...,
            (P_N, I_N), where P_1, ..., P_N are output tensor shape for each sample.
        idx_order (array-like): The ordering index of projected (and vectorised) features in decreasing variance.
        mean_ (array-like): Per-feature empirical mean, estimated from the training set, shape (I_1, I_2, ..., I_N).
        shape_in (tuple): Input tensor shapes, i.e. (I_1, I_2, ..., I_N).
        shape_out (tuple): Output tensor shapes, i.e. (P_1, P_2, ..., P_N).
    Examples:
        >>> import numpy as np
        >>> from kale.embed import MPCA
        >>> X = np.random.random((40, 20, 25, 20))
        >>> X.shape
        (40, 20, 25, 20)
        >>> mpca = MPCA(variance_explained=0.9)
        >>> X_transformed = mpca.fit_transform(X)
        >>> X_transformed.shape
        (40, 18, 23, 18)
        >>> X_transformed = mpca.transform(X, vectorise=True)
        >>> X_transformed.shape
        (40, 7452)
        >>> X_transformed = mpca.transform(X, vectorise=True, n_components=50)
        >>> X_transformed.shape
        (40, 50)
        >>> X_inverse = mpca.inverse_transform(X_transformed)
        >>> X_inverse.shape
        (40, 20, 25, 20)
    """

    def __init__(self, var_ratio=0.97, max_iter=1, vectorise=False, n_components=None):
        self.var_ratio = var_ratio
        if max_iter > 0 and isinstance(max_iter, int):
            self.max_iter = max_iter
        else:
            raise ValueError("Number of max iterations must be an integer and greater "
                             "than 0, but given %s" % max_iter)
        self.proj_mats = []
        self.vectorise = vectorise
        self.n_components = n_components

    def fit(self, X, y=None):
        """Fit the model with input training data X.

        Args
            X (array-like tensor): Input data, shape (n_samples, I_1, I_2, ..., I_N), where
                n_samples is the number of samples, I_1, I_2, ..., I_N are the dimensions of
                corresponding mode (1, 2, ..., N), respectively.
            y (None): Ignored variable.

        Returns:
            self (object). Returns the instance itself.
        """
        self._fit(X)
        return self

    def _fit(self, X):
        """Solve MPCA"""

        shape_ = X.shape  # shape of input data
        n_spl = shape_[0]  # number of samples
        n_dim = X.ndim

        self.shape_in = shape_[1:]
        self.mean_ = np.mean(X, axis=0)
        X_ = X - self.mean_
        
        # init
        phi = dict()
        # ev_sorted = dict()  # dictionary of eigenvectors for all modes/orders
        # lambdas = dict()  # dictionary of eigenvalues for all modes/orders
        # dictionary of cumulative distribution of eigenvalues for all modes/orders
        # cums = dict()
        shape_out = ()
        proj_mats = []

        for i in range(1, n_dim):
            for j in range(n_spl):
                # unfold the j_th tensor along the i_th mode
                X_ji = unfold(X_[j, :], mode=i - 1)
                if i not in phi:
                    phi[i] = 0
                phi[i] = phi[i] + np.dot(X_ji, X_ji.T)

        for i in range(1, n_dim):
            eig_values, eig_vectors = np.linalg.eig(phi[i])
            idx_sorted = (-1 * eig_values).argsort()
            # ev_sorted[i] = eig_vectors[:, idx_sorted]
            cum = eig_values[idx_sorted]
            var_tot = np.sum(cum)

            for j in range(1, cum.shape[0] + 1):
                if np.sum(cum[: j]) / var_tot > self.var_ratio:
                    shape_out += (j,)
                    break
            # cums[i] = cum            
            proj_mats.append(eig_vectors[:, idx_sorted][:, : shape_out[i - 1]].T)

        if self.vectorise and isinstance(self.n_components, int):
            if self.n_components > np.prod(self.shape_out):
                self.n_components = np.prod(self.shape_out)
                print("n_components can not exceed the multiplication of output tensor shapes, "
                      "the maximum number of components will be applied.")

        for i_iter in range(self.max_iter):
            phi = dict()
            for i in range(1, n_dim):  # ith mode
                if i not in phi:
                    phi[i] = 0
                for j in range(n_spl):
                    X_j = X_[j, :]  # jth tensor/sample
                    Xj_ = multi_mode_dot(
                        X_j,
                        [proj_mats[m] for m in range(n_dim - 1) if m != i - 1],
                        modes=[m for m in range(n_dim - 1) if m != i - 1],
                    )
                    Xj_unfold = unfold(Xj_, i - 1)
                    phi[i] = np.dot(Xj_unfold, Xj_unfold.T) + phi[i]

                eig_values, eig_vectors = np.linalg.eig(phi[i])
                idx_sorted = (-1 * eig_values).argsort()
                # lambdas[i] = eig_values[idx_sorted]
                proj_mats[i - 1] = eig_vectors[:, idx_sorted]
                proj_mats[i - 1] = (proj_mats[i - 1][:, : shape_out[i - 1]]).T

        tensor_pc = multi_mode_dot(X_, proj_mats, modes=[m for m in range(1, n_dim)])
        tensor_pc_vec = unfold(tensor_pc, mode=0)  # vectorise the tensor principal components
        # diagonal of the covariance of vectorised features
        tensor_pc_cov_diag = np.diag(np.dot(tensor_pc_vec.T, tensor_pc_vec))
        idx_order = (-1 * tensor_pc_cov_diag).argsort()

        self.proj_mats = proj_mats
        self.idx_order = idx_order
        self.shape_out = shape_out
        self.n_dim = n_dim

        return self

    def transform(self, X):
        """Perform dimension reduction on X

        Args:
            X (array-like tensor): Data to perform dimension reduction, shape (n_samples, I_1, I_2, ..., I_N).

        Returns:
            array-like tensor:
                Transformed data, shape (n_samples, P_1, P_2, ..., P_N) if self.vectorise==False.
                If self.vectorise==True, features will be sorted based on their explained variance ratio,
                shape (n_samples, P_1 * P_2 * ... * P_N) if self.n_components is None,
                and shape (n_samples, n_components) if self.n_component is not None.
        """
        _check_dim_shape(X, self.n_dim, self.shape_in)
        X -= self.mean_

        # tensor principal components
        tensor_pc = multi_mode_dot(X, self.proj_mats, modes=[m for m in range(1, self.n_dim)])

        if self.vectorise:
            tensor_pc = unfold(tensor_pc, mode=0)
            tensor_pc = tensor_pc[:, self.idx_order]
            if isinstance(self.n_components, int):
                tensor_pc = tensor_pc[:, : self.n_components]

        return tensor_pc

    def inverse_transform(self, X, add_mean=False):
        """Transform data in the shape of reduced dimension back to the original shape

        Args:
            X (array-like tensor): Data to be transformed back. If self.vectorise == False,
                shape (n_samples, P_1, P_2, ..., P_N), where P_1, P_2, ..., P_N are the
                reduced dimensions of of corresponding mode (1, 2, ..., N), respectively.
                If self.vectorise == True, shape (n_samples, self.n_components) or shape
                (n_samples, P_1 * P_2 * ... * P_N).
            add_mean (bool): Whether add the mean estimated from the training set to the output.
                Defaults to False.

        Returns:
            array-like tensor:
                Reconstructed tensor in original shape, shape (n_samples, I_1, I_2, ..., I_N)
        """
        # reshape X to tensor in shape (n_samples, self.shape_out) if X is vectorised
        if X.ndim <= 2:
            if X.ndim == 1:
                X = X.reshape((1, -1))
            n_spl = X.shape[0]
            n_feat = X.shape[1]
            if n_feat <= np.prod(self.shape_out):
                X_ = np.zeros((n_spl, np.prod(self.shape_out)))
                X_[:, : self.idx_order[: n_feat]] = X[:]
            else:
                raise ValueError("Feature dimension exceeds the shape upper limit.")
            
            X = fold(X_, mode=0, shape=((n_spl,) + self.shape_out))
            
        X_rec = multi_mode_dot(X, self.proj_mats, modes=[m for m in range(1, self.n_dim)],
                               transpose=True)

        if add_mean:
            # transpose to shape (n_samples, I_1, ..., I_N) to add mean
            X_rec += self.mean_
        
        return X_rec
