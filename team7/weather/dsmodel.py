import numpy as np
import pandas as pd
import gc
import datetime


class ModelApi:
    RFclf = None
    voting_clf = None
    RFRclf = None
    GBlower_model = None
    GBmid_model = None
    GBupper_model = None


def preprocess(df_name):
    weeks = df_name["Weeks"]
    dfyear = []
    dfmonth = []
    dfweek = []
    for i in weeks:
        year = int(i[0:4])
        month = int(i[5:7])
        day = int(i[8:])
        week = datetime.date(year, month, day).isocalendar()[1]
        dfyear.append(year)
        dfmonth.append(month)
        dfweek.append(week)
    df_name["Year"] = dfyear
    df_name['Month'] = dfmonth


def drought_cat(df_name):
    dfcopy = df_name.copy()
    drought = []
    points = dfcopy["DSCI"]
    for i in points:
        if i == 0:
            drought.append(-1)
        elif i <= 1:
            drought.append(0)
        elif i <= 2:
            drought.append(1)
        elif i <= 3:
            drought.append(2)
        elif i <= 4:
            drought.append(3)
        else:
            drought.append(4)
    dfcopy["Drought Cat"] = drought
    return dfcopy


def init_model():
    from sklearn.model_selection import train_test_split, KFold, cross_val_score
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.ensemble import VotingClassifier
    from sklearn.ensemble import GradientBoostingClassifier

    df = pd.read_csv("weather/static/data/training.csv")
    df["DSCI"] = df['D0'] + df['D1'] + df['D2'] + df['D3'] + df['D4']
    df["DSCI"] = df["DSCI"] / 100
    df = df.drop(columns=['Unnamed: 0', 'County', 'State', 'None', 'D0', 'D1', 'D2', 'D3', 'D4', 'ValidStart', 'ValidEnd'])
    dfnew = df[0:134480]
    preprocess(dfnew)

    dfnew = dfnew.drop(columns=['MapDate'])
    dfnew = dfnew.drop(columns=['Weeks'])
    dfnew.replace([np.inf, -np.inf], np.nan, inplace=True)
    dfnew.dropna(axis='columns')

    df3 = dfnew[dfnew['Year'] > 2015]
    y = df3["DSCI"]
    x = df3.drop(columns=['DSCI'])

    X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.25)
    from sklearn.ensemble import GradientBoostingRegressor
    # Set lower and upper quantile
    LOWER_ALPHA = 0.1
    UPPER_ALPHA = 0.9
    # Each model has to be separate
    GBlower_model = GradientBoostingRegressor(loss="quantile",
                                              alpha=LOWER_ALPHA)
    # The mid model will use the default loss
    GBmid_model = GradientBoostingRegressor(loss="ls")
    GBupper_model = GradientBoostingRegressor(loss="quantile",
                                              alpha=UPPER_ALPHA)

    # Fit models
    GBlower_model.fit(X_train, y_train)
    GBmid_model.fit(X_train, y_train)
    GBupper_model.fit(X_train, y_train)
    # ******** UPDATE ********
    ModelApi.GBlower_model = GBlower_model
    ModelApi.GBmid_model = GBmid_model
    ModelApi.GBupper_model = GBupper_model
    # ************************

    from sklearn.ensemble import RandomForestRegressor
    # creating a RF classifier
    RFRclf = RandomForestRegressor(n_estimators=50)
    # Training the model on the training dataset
    # fit function is used to train the model using the training sets as parameters
    RFRclf.fit(X_train, y_train)

    # ******** UPDATE ********
    ModelApi.RFRclf = RFRclf
    # ************************

    df_cate = df3.copy()
    df_cat = drought_cat(df_cate)

    y = df_cat["Drought Cat"]
    x = df_cat.drop(columns=['DSCI', 'Drought Cat'])
    X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.25)
    # Random Forest Classifier
    from sklearn.ensemble import RandomForestClassifier
    # creating a RF classifier
    RFclf = RandomForestClassifier(n_estimators=30)

    # Training the model on the training dataset
    # fit function is used to train the model using the training sets as parameters
    RFclf.fit(X_train, y_train)
    # ******** UPDATE ********
    ModelApi.RFclf = RFclf
    # ************************


    # creating a RF classifier
    GBclf = GradientBoostingClassifier(n_estimators=50)
    # Training the model on the training dataset
    # fit function is used to train the model using the training sets as parameters
    GBclf.fit(X_train, y_train)
    # creating a RF classifier
    KNclf = KNeighborsClassifier(n_neighbors=7)
    # Training the model on the training dataset
    # fit function is used to train the model using the training sets as parameters
    KNclf.fit(X_train, y_train)
    voting_clf = VotingClassifier(estimators=[('RF', RFclf), ('GB', GBclf), ('KNN', KNclf)], voting='soft',
                                  weights=[5, 1, 1])
    voting_clf.fit(X_train, y_train)
    # ******** UPDATE ********
    ModelApi.voting_clf = voting_clf
    # ************************
    del df_cat
    del df_cate
    del df3
    del dfnew
    del df
    gc.collect()


def pricing(df, amount_requested, drought_level, month):
    if ModelApi.RFclf is None or ModelApi.voting_clf is None or ModelApi.RFRclf is None or ModelApi.GBlower_model is None or ModelApi.GBmid_model is None or ModelApi.GBupper_model is None:
        init_model()
    xtest = df
    xtest['Month'] = month
    xtest['Year'] = 2022
    xtest = xtest.drop(columns=['Weeks'])
    RF = ModelApi.RFclf.predict(xtest)[0]
    VC = ModelApi.voting_clf.predict(xtest)[0]
    RFR = ModelApi.RFRclf.predict(xtest)[0]
    lower = ModelApi.GBlower_model.predict(xtest)[0]
    mid = ModelApi.GBmid_model.predict(xtest)[0]
    up = ModelApi.GBupper_model.predict(xtest)[0]

    difference = drought_level - VC
    ten = drought_level - up
    if ten < 0:
        ten = 0
    premium = amount_requested
    if difference <= 0:
        return {"premium": premium, "VC": VC, "difference": difference}
    elif difference >= 4:
        if ten > 3:
            premium = 0.012 * amount_requested
        elif ten > 2:
            premium = 0.04 * amount_requested
        elif ten >= 0:
            premium = 0.06 * amount_requested
    elif difference >= 3:
        if ten > 2:
            premium = 0.03 * amount_requested
        elif ten > 2:
            premium = 0.05 * amount_requested
        elif ten >= 0:
            premium = 0.13 * amount_requested
    elif difference >= 2:
        if ten > 1.5:
            premium = 0.03 * amount_requested
        elif ten > 1:
            premium = 0.07 * amount_requested
        elif ten > 0.5:
            premium = 0.14 * amount_requested
        elif ten >= 0:
            premium = 0.2 * amount_requested
        else:
            premium = 0.33 * amount_requested
    elif difference >= 1:
        if ten > 1:
            premium = 0.20 * amount_requested
        elif ten > 0.5:
            premium = 0.28 * amount_requested
        elif ten >= 0:
            premium = 0.60 * amount_requested
        else:
            premium = 0.76 * amount_requested
    return {"premium": premium, "VC": VC, "difference": difference}
