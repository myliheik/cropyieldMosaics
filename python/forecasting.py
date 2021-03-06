"""
2020-10-09 MY

Printing plots of forecasts from JRC, Satotilasto and EO predictions.

RUN:
python forecasting.py -i /Users/myliheik/Documents/myCROPYIELD/cropyieldMosaics/results/test1320 -y 2018 -n 
python forecasting.py -i /Users/myliheik/Documents/myCROPYIELD/cropyieldMosaics/results/test1320 -y 2018 -n -r -f

# To use meteorological features:
python forecasting.py -i /Users/myliheik/Documents/myCROPYIELD/cropyieldMosaics/results/test1320 -y 2018 -n -m

"""
import argparse
import textwrap

import pandas as pd
import pickle
import seaborn as sns
sns.set_theme(style="whitegrid")
import os.path
from pathlib import Path


def save_intensities(filename, arrayvalues):
    with open(filename, 'wb+') as outputfile:
        pickle.dump(arrayvalues, outputfile)

def load_intensities(filename):
    with open(filename, "rb") as f:
        data = pickle.load(f)
    return data

def forecast(predfile: str, year: int, saveForecast=False, saveGraph=False, showGraph=True, doRNN=False, doRNNfull=False):
    # Make forecasts from predictions

    basename = predfile.split('/')[-1][:-4]
    predfileJune = os.path.join(os.path.dirname(predfile), basename + 'June' + '.pkl')
    predfileJuly = os.path.join(os.path.dirname(predfile), basename + 'July' + '.pkl')
    predfileAugust = os.path.join(os.path.dirname(predfile), basename + 'August' + '.pkl')


    setti = predfile.split('/')[-2][-4:]
    ard = predfile.split('/')[-1][:-4]
    basepath = predfile.split('/')[1:-3]
    img = "Forecasts-" + setti + "-" + str(year) + ".png"
    imgpath = os.path.join(os.path.sep, *basepath, 'img', ard)
    imgfp = Path(os.path.expanduser(imgpath))
    imgfp.mkdir(parents=True, exist_ok=True)
    imgfile = os.path.join(imgfp, img)
    #print(setti)
    
    if setti == '1110':
        settix = 'winter wheat'
    if setti == '1120':
        settix = 'spring wheat'
    if setti == '1230':
        settix = 'rye'
    if setti == '1310':
        settix = 'feed barley'
    if setti == '1320':
        settix = 'malting barley'
    if setti == '1400':
        settix = 'oat'


    ##### Satotilasto:
    print('\nReading Luke satotilasto forecasts for crop', setti)
    fp = '/Users/myliheik/Documents/myCROPYIELD/ennusteetJRC/satotilastoLukeEnnusteet.csv'
    df = pd.read_csv(fp, sep=';', skiprows=4)
    if int(setti) == 1310 or int(setti) == 1320: # pitää hakea myös 1300
        sato = df[(df['Vuosi'] == year) & ((df['Vilja'] == int(setti)) | (df['Vilja'] == 1300))].sort_values(by = 'DOY', axis=0)['satoennuste']
    else:
        sato = df[(df['Vuosi'] == year) & (df['Vilja'] == int(setti))].sort_values(by = 'DOY', axis=0)['satoennuste']        
    #print(df[(df['Vuosi'] == year) & (df['Vilja'] == int(setti))])

    sato0 = pd.Series([None])
    sato1 = sato0.append(sato)
    
    ##### Random forest:
    # Read predictions:
    preds = load_intensities(predfile) 
    preds['year'] = preds['farmID'].str.split('_').str[0]
    average = preds[preds['year'] == str(year)].groupby(['ELY']).mean().mean()
    
    predsJune = load_intensities(predfileJune) 
    predsJune['year'] = predsJune['farmID'].str.split('_').str[0]
    averageJune = predsJune[predsJune['year'] == str(year)].groupby(['ELY']).mean().mean()

    predsJuly = load_intensities(predfileJuly) 
    predsJuly['year'] = predsJuly['farmID'].str.split('_').str[0]
    averageJuly = predsJuly[predsJuly['year'] == str(year)].groupby(['ELY']).mean().mean()

    predsAugust = load_intensities(predfileAugust) 
    predsAugust['year'] = predsAugust['farmID'].str.split('_').str[0]
    averageAugust = predsAugust[predsAugust['year'] == str(year)].groupby(['ELY']).mean().mean()

    
    d = {'Month': ['June', 'July', 'August','Final'], 'RF': [int(averageJune), int(averageJuly), int(averageAugust), int(average)], 'Satotilasto': sato1}
    output = pd.DataFrame(data=d)
        
    ####### JRC:    
    print('Reading JRC crop yield forecasts for crop', setti)   

    fp = '/Users/myliheik/Documents/myCROPYIELD/ennusteetJRC/JRCMARS4CASTs.txt'
    df = pd.read_csv(fp, sep=',', skiprows=5)

    if int(setti) == 1110 or int(setti) == 1120:
        jrcsetti = 1100
    if int(setti) == 1310 or int(setti) == 1320:
        jrcsetti = 1300
    if int(setti) == 1230:
        jrcsetti = 1230
    if int(setti) == 1400:
        jrcsetti = None # there is no JRC forecasts for oat 1400
    
    if jrcsetti is not None:
        sato2 = df[(df['Vuosi'] == year) & (df['Vilja'] == int(jrcsetti))].sort_values(by = 'DOY', axis=0).reset_index(drop=True)['ennuste']*1000
        #print(sato2)
        sato2[4] = None
        output = output.assign(JRC = sato2.values)
    
    ####### LSTM:
    print('Reading LSTM crop yield predictions for crop', setti) 
    predfile3D = load_intensities(os.path.join(os.path.dirname(predfile), 'ard3DPreds.pkl'))
    farmID3D = load_intensities(os.path.join(os.path.dirname(predfile), 'y3DfarmID.pkl'))
    
    if predfile3D.shape[0] != farmID3D.shape[0]:
        print("predfile3D and farmID3D numbers don't match!")
    
    predfile3D['year'] = farmID3D.str.split('_').str[0].values
    predictions = predfile3D[predfile3D['year'] == str(year)].mean(axis = 0)
    
    output = output.assign(LSTM = predictions[:-1].values.astype(int))  
    
    
    if doRNN:
        ####### RNN from histograms: 
        print('Reading RNN crop yield predictions for crop', setti) 
        testsetti = 'test' + setti
        predfile3D = load_intensities(os.path.join(os.path.dirname('/Users/myliheik/Documents/myCROPYIELD/RNNpreds/'), 
                                                   testsetti, 'RNNPreds.pkl'))
        fpRNN = 'farmID_test' + setti + '.pkl'
        farmID3D = load_intensities(os.path.join(os.path.dirname('/Users/myliheik/Documents/myCROPYIELD/dataStack/'),  fpRNN))

        if predfile3D.shape[0] != farmID3D.shape[0]:
            print("RNN predfile and farmID numbers don't match!")

        predfile3D['year'] = pd.Series(farmID3D).str.split('_').str[0].values
        predictionsRNN = predfile3D[predfile3D['year'] == str(year)].mean(axis = 0)

        output = output.assign(RNN = predictionsRNN[:-1].values.astype(int))  

    if doRNNfull:
        print('Reading RNN crop yield predictions from full data model for crop', setti)
        testsetti = 'test' + setti
        predfile3D = load_intensities(os.path.join(os.path.dirname('/Users/myliheik/Documents/myCROPYIELD/RNNpreds/'), 
                                                   testsetti, 'RNNPredsFull.pkl'))
        fpRNN = 'farmID_test' + setti + '.pkl'
        farmID3D = load_intensities(os.path.join(os.path.dirname('/Users/myliheik/Documents/myCROPYIELD/dataStack/'),  fpRNN))

        if predfile3D.shape[0] != farmID3D.shape[0]:
            print("RNN predfile and farmID numbers don't match!")

        predfile3D['year'] = pd.Series(farmID3D).str.split('_').str[0].values
        predictionsRNNfull = predfile3D[predfile3D['year'] == str(year)].mean(axis = 0)

        output = output.assign(RNNsuper = predictionsRNNfull[:-1].values.astype(int))          

    print("\nNumber of farms in prediction set: ", len(preds[preds['year'] == str(year)]))
    
    ###### Finally combining:
    output = output.set_index('Month')
    output.columns.name = 'Method'
    s = output.stack()
    s.name = 'Crop yield'
    ss = s.reset_index()


    print('\nThe RF predicted August crop yield for Finland in', year, 'was', int(averageAugust), 'kg/ha for', setti, '.')
    print('The LSTM predicted August crop yield for Finland in', year, 'was', int(predictions[12]), 'kg/ha for', setti, '.')
    if doRNN:
        print('The RNN predicted August crop yield for Finland in', year, 'was', int(predictionsRNN[2:3]), 'kg/ha for', setti, '.')
    if doRNNfull:
        print('The RNNsuper predicted August crop yield for Finland in', year, 'was', int(predictionsRNNfull[2:3]), 'kg/ha for', setti, '.')
    if jrcsetti is not None:
        print('The JRC crop yield August forecast for Finland in', year, 'was', int(sato2[2:3]), 'kg/ha for', setti, '.')
    print('The real crop yield for Finland in', year, 'was', int(sato[2:3]), 'kg/ha for', setti, '.')

    
    # Draw a nested barplot 
    g = sns.catplot(
        data=ss, kind="bar",
        x="Month", y="Crop yield", hue="Method",
        ci="sd", palette="dark", alpha=.6, height=6
    )
    g.despine(left=True)
    g.set_axis_labels("", "Crop yield (kg/ha)")
    g.legend.set_title("")
    g.set(title = "Crop " + settix + " for year " + str(year))
    g.axes[0][0].axhline(y = int(sato[2:3]), color='red', linewidth=2, alpha=.7)
    if saveGraph:
        print('\nSaving the bar plot into', imgfile)
        g.savefig(imgfile)
    
    if saveForecast:
        file = "Forecasts-" + setti + "-" + str(year) + ".csv"
        filepath = os.path.join(os.path.sep, *basepath, 'forecasts', ard)
        fp = Path(os.path.expanduser(filepath))
        fp.mkdir(parents=True, exist_ok=True)
        datafile = os.path.join(fp, file)
        print('\nSaving the forecasts into', datafile)
        output.to_csv(datafile)
    


# HERE STARTS MAIN:

def main(args):
    try:
        if not args.pred_dir :
            raise Exception('Missing predictions directory argument. Try --help .')

        print(f'\nforecasting.py')
        print(f'\nPredictions in: {args.pred_dir}')


        if args.use_2Dmeteo:
            print(f'\nUsing ARD + meteorological features, for 2D only.')
            predfile = os.path.join(args.pred_dir, 'ard2DmeteoPreds.pkl')
        else:
            predfile = os.path.join(args.pred_dir, 'ard2DPreds.pkl')

        forecast(predfile, args.year, saveGraph=True, saveForecast=args.saveForecasts, doRNN=args.doRNN, doRNNfull=args.doRNNfull)
        
        
        print(f'\nDone.')

    except Exception as e:
        print('\n\nUnable to read input or write out statistics. Check prerequisites and see exception output below.')
        parser.print_help()
        raise e


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent(__doc__))

    parser.add_argument('-i', '--pred_dir',
                        help='Directory for predictions directory.',
                        type=str,
                        default='.')
        
    parser.add_argument('-y', '--year',
                        help='Year, default 2018.',
                        type=int,
                        default=2018)

    parser.add_argument('-m', '--use_2Dmeteo',
                        help='Use additional meteorological features.',
                        default=False,
                        action='store_true')

    parser.add_argument('-n', '--saveForecasts',
                        help='Save forecasts into file.',
                        default=False,
                        action='store_true')
    parser.add_argument('-r', '--doRNN',
                        help='Use also RNN predictions.',
                        default=False,
                        action='store_true')
    parser.add_argument('-f', '--doRNNfull',
                        help='Use also full data RNN predictions.',
                        default=False,
                        action='store_true')

    parser.add_argument('--debug',
                        help='Verbose output for debugging.',
                        action='store_true')

    args = parser.parse_args()
    main(args)
