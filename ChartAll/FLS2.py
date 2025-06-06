import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0" #per disattivare ONEDNN

import tensorflow as tf
print(tf.__version__)

(x_train, y_train), (x_test, y_test)= tf.keras.datasets.mnist.load_data(path='mnist.npz')
assert x_train.shape == (60000, 28, 28)  #60000 immagini 28x28
assert y_train.shape == (60000,)         #60000 label
assert x_test.shape == (10000, 28, 28)   #10000 immagini 28x28
assert y_test.shape == (10000,)          #10000 label


ds_train = tf.data.Dataset.from_tensor_slices((x_train, y_train))  #crea un dataset dove ogni elemento è una tupla (x[i], y[i]) per il ds TRAIN
ds_test = tf.data.Dataset.from_tensor_slices((x_test, y_test))     #crea un dataset dove ogni elemento è una tupla (x[i], y[i]) per il ds TEST

ds_train = ds_train.batch(128)
ds_test = ds_test.batch(128)


n_client = int(input("Inserisci il numero di client: "))
print("n_client: ", n_client)


#SUDDIVIDO IN TERMINI DI BATCH
num_batch_train_elements = len(ds_train)
div_train = num_batch_train_elements / n_client

if div_train.is_integer():
    div_train = int(div_train)
else: div_train = int(div_train) +1
print("num_batch_train_elements: ", num_batch_train_elements, div_train)


#NON divido il ds_test (serve per evaluate)
array_ds_train = []
ds = 0
i = 0

for nclient in range(n_client):
    if i+div_train <= len(ds_train):
        ds = ds_train.skip(i).take(div_train)
    else:
        ds = ds_train.skip(i)
    array_ds_train.append(ds)
    i+=div_train

for i,client in enumerate(array_ds_train):
    print(f"client {i} num batch: {len(client)}")

#CREO E ADDESTRO IL MODELLO
#costruzione modello (rete neurale contenuta in model)
def create_model():
    model = tf.keras.models.Sequential([ #modello sequenziale (ogni layer riceve l'output del layer precedente) in keras
        tf.keras.layers.Input(shape=(28, 28)), #appiattisce l'input (immagine di dimensioni MNIST matrice 28x28) in un vettore unidimensionale di 784 elementi
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'), #crea uno strato denso (connesso con il layer precedente) di 128 nodi e come funzione di attivazione la ReLU
        tf.keras.layers.Dense(10) #crea un altro strato denso con 10 nodi (classi finali del ds), no funzione di attivazione è l'output
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),   #Softmax trasforma i logits in probabilità
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )
    return model


rounds_number = 10

global_model = create_model()
client_models = []

rounds = []
accuracy = []


for client in range(n_client):
    client_models.append(create_model())


loss, s_cat_acc = global_model.evaluate(ds_test, verbose=1)
print(f"Loss modello globale: {loss}")
print(f"Sparse categorical accuracy modello globale: {s_cat_acc}")


for r in range(rounds_number):

    print(f"Round {r+1}")
    for i,client_model in enumerate(client_models):
        client_model.set_weights(global_model.get_weights())
        client_model.fit(array_ds_train[i], epochs=1, validation_data=ds_test)

    weights = [client_model.get_weights() for client_model in client_models]
    lunghezze = [len(ds) for ds in array_ds_train]
    totale = sum(lunghezze)

    new_global_weight = [
        sum((lunghezze[n_c] / totale) * weights[n_c][p] for n_c in range(len(weights)))
        for p in range(len(weights[0])) #tutti i pesi hanno stessa dimensione (pesi + bias) [livelli]
    ]

    global_model.set_weights(new_global_weight)
    loss, s_cat_acc = global_model.evaluate(ds_test, verbose=0)
    rounds.append(r + 1)
    accuracy.append(s_cat_acc)


loss, s_cat_acc = global_model.evaluate(ds_test, verbose=1)
print(f"Loss modello globale: {loss}") #indica quanto sbaglia e con quanta sicurezza
print(f"Sparse categorical accuracy modello globale: {s_cat_acc}") #percentuale di accuratezza della risposta


def get_data2():
    return n_client, rounds, accuracy