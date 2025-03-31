# Get EEG signal
# signal = pyedflib.highlevel.read_edf(str(cassette_path / psg_filename))[0][0]
#
# Sleep waves
# Delta: 0-3.5 Hz
# Theta: 4-7.5 Hz
# Alpha: 8-13 Hz
# Beta: 14-30 Hz
# Gamma 30-100 Hz

from sklearn.preprocessing import StandardScaler as sc, MinMaxScaler as mc, FunctionTransformer
from sklearn.decomposition import KernelPCA
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Lasso
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn import svm
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
import xgboost as xgb
import optuna

'''This module assumes that the data is already divided into training, validation and testing data. The
module can be divided into 4 steps:
1. Bandpass filtering
2. Data regularization 
3. Dimensionality reduction
4. Machine learning model

Each of the possible combinations of the strategies are then addressed in individual sklearn pipelines.'''

### Preliminaries
# Parameters
k = 5 # number of folds for k-fold CV

# Split data intro training and testing sets
X, y = load_data()
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                    stratify=y)

# Generate folds for k-fold CV
cv = StratifiedKFold(shuffle=True)
n_con = len(X_train) // k # safe lower upper bound for n of a fold

### List of dimensionality reduction techniques and classifiers
# Maps dimensionality reduction technique to its wrapper
dim_reduction_mappings = {
        None: None,
        'PCA', PCA_wrapper,
        'SVD', SVD_wrapper
}

# Maps classifier to its wrapper
clf_mappings = {
        'SVM': SVM_wrapper,
        'random_forest': random_forest_wrapper,
        'kNN': kNN_wrapper
}

### Implementation of dimensionality reduction techniques and classifiers
def kNN_wrapper(trial):
    n_neighbors = trial.suggest_int('n_neighbors', 1, n_con, log=True)
    return KNeighborsClassifier(n_neighbors=n_neighbors)

### Define objective/pipeline and run optimization
def objective(trial):
    # Bandpass filter
    alpha_divs = trial.suggest_int('alpha_divs', 1, 2)
    beta_divs = trial.suggest_int('beta_divs', 1, 4)
    gamma_divs = trial.suggest_int('gamma_divs', 1, 5)
    bp_filter = BPFilter(alpha_divs, beta_divs, gamma_divs)

    # Normalization
    scalar = StandardScalar()

    # Dimensionality reduction
    dim_reduction = trial.suggest_categorical(
            'dim_reduction',
            list(dim_reduction_mappings.keys()))

    if dim_reduction is None:
        dim_reduction = 'passthrough'
    else:
        dim_reduction = dim_reduction_mappings[dim_reduction](trial)

    # Classification
    clf = trial.suggest_categorical('clf', list(clf_mappings.keys()))
    clf = clf_mappings[clf](trial)

    # Build pipeline
    pipeline = Pipeline([
        ('bp_filter', bp_filter),
        ('scalar', scalar),
        ('dim_reduction', dim_reduction),
        ('clf', clf)
    ])

    # K-fold cross-validation
    return 1 - cross_val_score(pipeline, X_train, y_train, cv=cv,
                               scoring='accuracy').mean()

# Run optimization
if __name__ == '__main__':
    study = optuna.create_study()
    study.optimize(objective, n_trials=50)
    
    # Implement optimization results

### OLD CODE TO BE REFACTORED

#Kernalized PCA
def KPCA(x, n_componenets, kernel, gamma):
    kpca = KernelPCA(n_components= n_componenets, kernel = kernel, gamma = gamma, n_jobs=-1)
    x_new = kpca.fit_transform(x)
    return x_new

#SVD
def SVD(x, n_components):
    trun_svd = TruncatedSVD(n_components = n_components)
    x_new = trun_svd.fit_transform(x)
    return x_new

'''#LASSO (needs y?)
def Lasso_dim_red(x,y,alpha):
    lasso_dr = Lasso(alpha = alpha)
    lasso_dr.fit(x = x, y = y)
    return x,y'''

#LDA
def LDA(x):
    lda_solver = LinearDiscriminantAnalysis()
    lda_solver.fit_transform(x)
    return x
    
#Classifiers

#Kernalized SVM
def kernal_SVM(x_train,y_train,x_test, kernal):
    k_SVM = svm.SVC(kernal = kernal)
    k_SVM.fit(x_train, y_train)
    y_pred = k_SVM.predict(x_test)
    return y_pred

#DT
def DT(x_train, y_train, x_test, criterion):
    dec_tree = DecisionTreeClassifier(criterion = criterion)
    dec_tree.fit(x_train,y_train)
    y_pred = dec_tree.predict(x_test)
    return y_pred
    
#Random forest
def RF(x_train, y_train, x_test, n_estimators, criterion):
    rf_claf = RandomForestClassifier(n_estimators = n_estimators, criterion = criterion)
    rf_claf.fit(x_train,y_train)
    y_pred = rf_claf.predict(x_test)
    return y_pred
  
#Random Forest with xgboost
def xg_boost(x_train, y_train, x_test, booster, max_depth):
    xgb_claf = xgb.train(booster = booster, max_depth = max_depth,d_train = [(x_train,y_train)])
    y_pred = xgb_claf.predict(x_test)
    return y_pred

#Neural network
def NN(x_train, y_train, x_test, solver, alpha, hidden_layer_sizes):
    nn_claf = MLPClassifier(solver = solver, alpha = alpha, hidden_layer_sizes = hidden_layer_sizes)
    nn_claf.fit(x_train,y_train)
    y_pred = nn_claf.predict(x_test)
    return y_pred

#Pipelines
