from nltk.tokenize import SyllableTokenizer, RegexpTokenizer

def find_syllable_count_from_sentences(sentence):
    word_tokenizer = RegexpTokenizer(r"\w+")
    words = word_tokenizer.tokenize(sentence)
    count = 0
    for word in words:
        count += find_syllable_count_from_word(word)
    return count

def find_syllable_count_from_word(word):
    syllable_tokenizer = SyllableTokenizer()
    syllables = syllable_tokenizer.tokenize(word) 
    return len(syllables)