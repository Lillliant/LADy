from cmn.semeval import SemEvalReview
import pandas as pd
import csv

def save_latent_reviews(data, output, format='pkl'):
    reviews = SemEvalReview.load(data, lr_extract=True)
    if format == 'pkl':
        output_ = f'{output}.pkl'
        pd.to_pickle(reviews, output_)
    elif format == 'csv':
        output_ = f'{output}.csv'
        with open(output, 'w') as f:
            writer = csv.DictWriter(f, ['id', 
                                        'text', 
                                        'sentences',
                                        'aos',
                                        'lang',
                                        'orig'])
            writer.writeheader()
            for r in reviews:
                writer.writerow(r.to_dict())

datasets = [
        ('../data/raw/semeval/2015SB12/ABSA15_RestaurantsTrain/ABSA-15_Restaurants_Train_Final.xml', './semeval-15-restaurants'),
]

for data, output in datasets:
    save_latent_reviews(data, output, 'pkl')
    reviews = pd.read_pickle(f'{output}.pkl')
    print(len(reviews))
    save_latent_reviews(data, output, 'csv')
    reviews = pd.read_csv(f'{output}.csv')
    for r in reviews:
        print(r)
    print(len(reviews))