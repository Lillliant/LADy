import os
from tqdm import tqdm
import xml.etree.ElementTree as et

#nlp = spacy.load("en_core_web_sm")  # en_core_web_trf for transformer-based; error ==> python -m spacy download en_core_web_sm

from cmn.review import Review

class SemEvalReview(Review):

    def __init__(self, id, sentences, time, author, aos): super().__init__(self, id, sentences, time, author, aos)

    @staticmethod
    # lr_extract is the flag for extracting reviews with no aspects (latent review)
    def load(path, lr_extract=False):
        if str(path).endswith('.xml'): return SemEvalReview._xmlloader(path, lr_extract)
        return SemEvalReview._txtloader(input, lr_extract)

    @staticmethod
    def _txtloader(path, lr_extract=False):
        reviews = []
        with tqdm(total=os.path.getsize(path)) as pbar, open(path, "r", encoding='utf-8') as f:
            for i, line in enumerate(f.readlines()):
                pbar.update(len(line))
                sentence, aos = line.split('####')
                aos = aos.replace('\'POS\'', '+1').replace('\'NEG\'', '-1').replace('\'NEU\'', '0')

                # for the current datafile, each row is a review of single sentence!
                # sentence = nlp(sentence)
        
        return reviews

    @staticmethod
    def _xmlloader(path, lr_extract=False):
        reviews_list = []
        xtree = et.parse(path).getroot()
        if xtree.tag == 'Reviews':   reviews = [SemEvalReview._parse(xsentence, lr_extract) for xreview in tqdm(xtree) for xsentences in xreview for xsentence in xsentences]
        if xtree.tag == 'sentences': reviews = [SemEvalReview._parse(xsentence, lr_extract) for xsentence in tqdm(xtree)]

        return [r for r in reviews if r]

    # converts from character index to token index
    @staticmethod
    def _map_idx(aspect, text):
        # aspect: ('token', from_char, to_char)
        text_tokens = text[:aspect[1]].split()
        # to fix if  "aaaa ,b, c" ",b c" if b is the aspect
        if len(text_tokens) > 0 and not text[aspect[1] - 1].isspace(): text_tokens.pop()
        aspect_tokens = aspect[0].split()

        # tmp = [*text] #mutable string :)
        # # these two blank space add bug to the char indexes for aspects if a sentence have multiple aspects!
        # tmp[aspect[1]: aspect[2]] = [' '] + [*aspect[0]] + [' ']
        # text = ''.join(tmp)

        return [i for i in range(len(text_tokens), len(text_tokens) + len(aspect_tokens))]

    @staticmethod
    def _parse(xsentence, lr_extract):
        id = xsentence.attrib["id"]
        aos = []; aos_cats = []
        for element in xsentence:
            if element.tag == 'text': sentence = element.text # we consider each sentence as a signle review
            elif element.tag == 'Opinions':#semeval-15-16
                #<Opinion target="place" category="RESTAURANT#GENERAL" polarity="positive" from="5" to="10"/>
                for opinion in element:
                    # latent review: defined as a review with opinion but no aspect (target)
                    if lr_extract:
                        if not opinion.attrib["target"] == 'NULL': continue
                        category = opinion.attrib["category"] # 'RESTAURANT#GENERAL'
                        sentiment = opinion.attrib["polarity"].replace('positive', '+1').replace('negative', '-1').replace('neutral', '0') #'+1'
                        aos.append(([-1], [], sentiment, opinion.attrib["category"])) #('NULL', 0, 0) has no token index
                        aos_cats.append(category)
                    else:
                        if opinion.attrib["target"] == 'NULL': continue
                        # we may have duplicates for the same aspect due to being in different category like in semeval 2016's <sentence id="1064477:4">
                        aspect = (opinion.attrib["target"], int(opinion.attrib["from"]), int(opinion.attrib["to"])) #('place', 5, 10)
                        # we need to map char index to token index in aspect
                        aspect = SemEvalReview._map_idx(aspect, sentence)
                        category = opinion.attrib["category"] # 'RESTAURANT#GENERAL'
                        sentiment = opinion.attrib["polarity"].replace('positive', '+1').replace('negative', '-1').replace('neutral', '0') #'+1'
                        aos.append((aspect, [], sentiment, opinion.attrib["target"]))
                        aos_cats.append(category)
                aos = sorted(aos, key=lambda x: int(x[0][0])) #based on start of sentence

            elif element.tag == 'aspectTerms':#semeval-14
                #<aspectTerm term="table" polarity="neutral" from="5" to="10"/>
                for opinion in element:
                    if lr_extract:
                        if not opinion.attrib["term"] == 'NULL': continue
                        sentiment = opinion.attrib["polarity"].replace('positive', '+1').replace('negative', '-1').replace('neutral', '0') #'+1'
                        aos.append(([-1], [], sentiment, opinion.attrib["term"]))
                    else:
                        if opinion.attrib["term"] == 'NULL': continue
                        # we may have duplicates for the same aspect due to being in different category like in semeval 2016's <sentence id="1064477:4">
                        aspect = (opinion.attrib["term"], int(opinion.attrib["from"]), int(opinion.attrib["to"])) #('place', 5, 10)
                        # we need to map char index to token index in aspect
                        aspect = SemEvalReview._map_idx(aspect, sentence)
                        sentiment = opinion.attrib["polarity"].replace('positive', '+1').replace('negative', '-1').replace('neutral', '0') #'+1'
                        aos.append((aspect, [], sentiment, opinion.attrib["term"]))
                aos = sorted(aos, key=lambda x: int(x[0][0])) #based on start of sentence

            elif element.tag == 'aspectCategories':  # semeval-14
                for opinion in element:
                    #<aspectCategory category="food" polarity="neutral"/>
                    aos_cats.append(opinion.attrib["category"])

        #sentence = nlp(sentence) # as it does some processing, it destroys the token idx for aspect term
        tokens = sentence.split()
        # to fix ",a b c," to "a b c"
        # to fix '"sales" team' to 'sales team' => semeval-14-labptop-<sentence id="1316">
        # todo: fix 'Food-awesome.' to 'food awesome' => semeval-14-restaurant-<sentence id="1817">
        for i, (idxlist, o, s, aspect_token) in enumerate(aos):
            for j, idx in enumerate(idxlist): tokens[idx] = aspect_token.split()[j].replace('"', '')
            aos[i] = (idxlist, o, s)
        return Review(id=id, sentences=[[str(t).lower() for t in tokens]], time=None, author=None,
                      aos=[aos], lempos=None,
                      parent=None, lang='eng_Latn', category=aos_cats) if aos else None

