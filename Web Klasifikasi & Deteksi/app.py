from flask import Flask,render_template,url_for,request, redirect
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import BernoulliNB
import string
import re
import pickle
from spacy import load, displacy
from flask_mysqldb import MySQL
import tweepy

auth = tweepy.auth.OAuthHandler('Mq7nSOazSivbdIwAWd8o3lgm9', 'tBhg2QwOLgeykzUUkOrdzjnGJUF2Y3TuPizZoer0yktUGAwcgk')
auth.set_access_token('1073044154379169792-dZewtzOoExrCtsPfMevmWY8prk6zuX', 'JY7aVXJur41SuEJ0Jb3sw6WwTs5JispjttVopksuzkaBM')
api = tweepy.API(auth)

def ProTweets(text):
    text = str(text).lower()
    text = re.sub(r"(?:\@|https?\://)\S+", "", str(text))
    text = "".join([char for char in text if char not in string.punctuation])
    text = re.sub('http\S+', '', text)
    return text
    
def get_tweets(text_query):
    data = []
    count = 10
    tweets = tweepy.Cursor(api.search, 
                        q=text_query,
                        lang="id").items(count)
    for tweet in tweets :
        tweet = data.append(tweet.text)
    return data
    
app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flaskdb'
mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('home.html')
    
    
@app.route('/Tampilkan Hasil')
def tampil():
    cur = mysql.connection.cursor()
    cur.execute("SELECT Tweet, Prediksi, Lokasi FROM dbd")
    rv = cur.fetchall()
    cur.close()
    return render_template('layout.html', dbd=rv)
    
@app.route("/Peta Persebaran")
def peta():
    cur = mysql.connection.cursor()
    cur.execute("SELECT langitude, longitude FROM tempat JOIN dbd ON tempat.nama_lokasi=dbd.Lokasi")
    locations = cur.fetchall()
    cur.close()
    return render_template('peta.html', locations=locations)

@app.route('/prediksi',methods=['POST'])
def predict():
    df= pd.read_excel("training&valid.xlsx")
    df['Tweet'] = df['Tweet'].apply(lambda x: ProTweets(x))
    df['Label'] = df['Label'].map({'Bukan Kasus': 0, 'Kasus': 1})
    X = df['Tweet']
    y = df['Label']
    
    # Extract Feature With CountVectorizer
    from sklearn.model_selection import train_test_split
    X_train, X_valid, y_train, y_valid = train_test_split(X, y,test_size=0.25, random_state=10)
    cv = CountVectorizer(ngram_range=(1,1))
    X_train_count = cv.fit_transform(X_train)
    X_valid_count = cv.transform(X_valid)
    
    # Memanggil Model Klasifikasi
    f = open('model_unigram.pickle', 'rb')
    clf = pickle.load(f)
    f.close()
    
    # Memanggil Model NER
    link_to_model = 'model_ner_perbaikan'
    ner = load(link_to_model)

    
    # Predict input
    if request.method == 'POST':
        tweet = request.form['tweet']
        get_tweet = get_tweets(tweet)
        for i in get_tweet:
            if i != None:
                data = ProTweets(i)
                vect = cv.transform([data])
                my_prediction = clf.predict(vect)
                if my_prediction == 'Kasus' :
                    pred_lokasi = ner(i)
                    for ent in pred_lokasi.ents:
                        if ent.label_ == 'lokasi'  :
                            cur = mysql.connection.cursor()
                            cur.execute("INSERT INTO DBD (Tweet, Prediksi, Lokasi) VALUES (%s,%s,%s)",(i,'Kasus',ent.text))
                            mysql.connection.commit()
                            break
                    else :
                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO DBD (Tweet, Prediksi, Lokasi) VALUES (%s,%s,%s)",(i,'Kasus','Tidak Ditemukan Lokasi'))
                        mysql.connection.commit()
                else :
                    cur = mysql.connection.cursor()
                    cur.execute("INSERT INTO DBD (Tweet, Prediksi, Lokasi) VALUES (%s,%s, %s)",(i,'Bukan Kasus','Tidak Ditemukan Lokasi'))
                    mysql.connection.commit()
        else :
            return redirect(url_for('home'))
           
            
        
    

if __name__ == "__main__":
    app.run(debug=True)