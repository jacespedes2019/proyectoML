import streamlit as st
import pandas as pd
from datetime import datetime
import joblib
import matplotlib.pyplot as plt


# Función para cargar las agrupaciones desde los CSV manteniendo el formato
def load_grouped_means():
    mean_by_month_df = pd.read_csv('mean_by_month_.csv')
    mean_by_week_df = pd.read_csv('mean_by_week_.csv')
    
    # Convertir los DataFrames a Series con índices multi-nivel
    mean_by_month_ = mean_by_month_df.set_index(['ITEMID', 'MONTH', 'INVENTLOCATIONID'])['MEAN_BY_MONTH']
    mean_by_week_ = mean_by_week_df.set_index(['ITEMID', 'WEEK_OF_MONTH', 'INVENTLOCATIONID'])['MEAN_BY_WEEK']
    
    # Convertir las Series a diccionarios
    mean_by_month_dict = mean_by_month_.groupby(level=[0, 1, 2]).mean().to_dict()
    mean_by_week_dict = mean_by_week_.groupby(level=[0, 1, 2]).mean().to_dict()
    
    return mean_by_month_dict, mean_by_week_dict

mean_by_month_, mean_by_week_ = load_grouped_means()

# Definición de la función preprocessing_X_new
def preprocessing_X_new(df):
    df['SALESPRICE'] = df['SALESPRICE'].astype('float')
    df.loc[:, 'SALESPRICE'] = df['SALESPRICE'] * (1 - df['LINEPERCENT'] / 100)
    df['SALESPRICE'] = df['SALESPRICE'].astype('float')

    df['DATE'] = pd.to_datetime(pd.to_datetime(df['CREATEDDATETIMECOPY1']).dt.date)
    df = date_features(df)
    
    # Calcular medias por mes y por semana usando las agrupaciones cargadas
    df.loc[:,'MEAN_BY_MONTH'] = df.set_index(['ITEMID','MONTH', 'INVENTLOCATIONID']).index.map(mean_by_month_)
    df.loc[:,'MEAN_BY_WEEK'] = df.set_index(['ITEMID','WEEK_OF_MONTH', 'INVENTLOCATIONID']).index.map(mean_by_week_)

    #df['MEAN_BY_MONTH']=1
    #df['MEAN_BY_WEEK']=1
    
    cat_features = ['DLVMODE', 'INVENTLOCATIONID','YEAR','MONTH','DAY_OF_WEEK','DAY_OF_YEAR','DAY_OF_MONTH','WEEK_OF_YEAR']
    for col in cat_features:
        df[col] = df[col].astype('category')

    #df = df.drop(columns=['CREATEDDATETIMECOPY1','ITEMID','DATE','LINEPERCENT','QUARTER','WEEK_OF_MONTH'])
    return df

# Función date_features
def date_features(df):
    df['YEAR'] = df['DATE'].dt.year
    df['MONTH'] = df['DATE'].dt.month
    df['WEEK_OF_MONTH'] = df['DATE'].dt.day // 7 + 1
    df['DAY_OF_WEEK'] = df['DATE'].dt.dayofweek
    df['QUARTER'] = df['DATE'].dt.quarter
    df['DAY_OF_YEAR'] = df['DATE'].dt.dayofyear
    df['WEEK_OF_YEAR'] = df['DATE'].dt.isocalendar().week
    df['DAY_OF_MONTH'] = df['DATE'].dt.day
    return df

# Títulos del formulario
st.title('Formulario de Entrada de Datos')

# Listas desplegables para los valores de selección
item_ids = [
    "1R0739", "1R0751", "1R0762", "1R1804", "1R1807", "7W2326", "8F9866",
    "66100", "1106331", "1561200", "2934053", "3096931-406", "3223155",
    "3261644", "3466688", "3608960", "3619554", "4385386", "5280585"
]

dlvmodes = ["Mostrador", "Recoge_cliente", "Paqueteo"]

inventlocationids = [1, 100, 50, 151, 20, 11, 13, 152, 205, 29]

st.session_state.data = pd.DataFrame(columns=["ITEMID", "SALESPRICE", "LINEPERCENT", "CREATEDDATETIMECOPY1", "DLVMODE", "INVENTLOCATIONID"])

# Verificar si el DataFrame ya tiene una fila
if len(st.session_state.data) == 0:
    # Campos del formulario
    with st.form(key='my_form'):
        itemid = st.selectbox('ITEMID', item_ids)
        salesprice = st.number_input('SALESPRICE', min_value=0.0, format="%.2f")
        linepercent = st.number_input('LINEPERCENT', min_value=0.0, format="%.2f")
        
        # Widgets para la fecha y la hora
        date = st.date_input('Fecha', datetime.now().date())
        time = st.time_input('Hora', datetime.now().time())
        
        dlvmode = st.selectbox('DLVMODE', dlvmodes)
        inventlocationid = st.selectbox('INVENTLOCATIONID', inventlocationids)

        # Botón de envío
        submit_button = st.form_submit_button(label='Enviar')

    # Guardar datos en el DataFrame y mostrarlo
    if submit_button:
        # Combinar la fecha y la hora en un solo valor de datetime
        createddatetimecopy1 = datetime.combine(date, time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Crear una nueva fila con los datos ingresados
        new_data = {
            "ITEMID": itemid,
            "SALESPRICE": salesprice,
            "LINEPERCENT": linepercent,
            "CREATEDDATETIMECOPY1": createddatetimecopy1,
            "DLVMODE": dlvmode,
            "INVENTLOCATIONID": inventlocationid
        }        
        # Añadir la nueva fila al DataFrame en session_state
        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_data])], ignore_index=True)
        
        columns_ = st.session_state.data.columns
        X_week = pd.DataFrame(columns=columns_)

        for d in range(5):
            X_new_ = st.session_state.data.copy()
            X_new_['CREATEDDATETIMECOPY1'] = pd.to_datetime(X_new_['CREATEDDATETIMECOPY1'])
            X_new_['CREATEDDATETIMECOPY1'] += pd.Timedelta(days=d)
            X_new_['CREATEDDATETIMECOPY1'] = X_new_['CREATEDDATETIMECOPY1'].dt.strftime('%Y-%m-%d %H:%M:%S')
            X_week = pd.concat([X_week, X_new_], ignore_index=True)
        
        # Ejecutar la función de preprocesamiento
        processed_data = preprocessing_X_new(X_week)
        
        plot_data= processed_data.copy()
        processed_data= processed_data.drop(columns=['CREATEDDATETIMECOPY1', 'ITEMID', 'DATE', 'LINEPERCENT','QUARTER','WEEK_OF_MONTH'])

        # Cargar y aplicar el modelo de ML
        filename_ = f'Modelos/model_{itemid}.sav'
        loaded_model = joblib.load(filename_)
        
        # Asegúrate de que las columnas estén en el mismo orden que cuando se entrenó el modelo
        expected_columns = loaded_model.feature_names_in_
        processed_data = processed_data[expected_columns]
        
        # Asumimos que el modelo predice la columna 'UNITS_SOLD'
        y_pred_new = loaded_model.predict(processed_data)
        
        # Añadir las predicciones al DataFrame
        plot_data['UNITS_SOLD'] = y_pred_new
        
        st.write('## Datos Ingresados:')
        st.write('**ITEMID:**', itemid)
        st.write('**SALESPRICE:**', salesprice)
        st.write('**LINEPERCENT:**', linepercent)
        st.write('**CREATEDDATETIMECOPY1:**', createddatetimecopy1)
        st.write('**DLVMODE:**', dlvmode)
        st.write('**INVENTLOCATIONID:**', inventlocationid)
        
        # Mostrar el DataFrame actualizado
        st.write('## DataFrame Actualizado:')
        st.dataframe(plot_data)
        
        # Graficar los resultados
        st.write('## Predicción de Unidades Vendidas:')
        #fig, ax = plt.subplots()
        #plot_data['DATE'] = pd.to_datetime(plot_data['CREATEDDATETIMECOPY1']).dt.date
        #plot_data = plot_data.sort_values(by='DATE')
        # Ajustar el tamaño de la fuente en la gráfica
        # Rotar las etiquetas del eje x para evitar la superposición
        #ax.plot(plot_data['DATE'], plot_data['UNITS_SOLD'], marker='o')
        #ax.set_xlabel('Fecha')
        #ax.set_ylabel('Unidades Vendidas')
        #ax.set_title('Unidades Vendidas por Día')
        #ax.tick_params(axis='x', rotation=45)
        #st.pyplot(fig)
        
        st.write("Total de unidades a vender en la semana: ", y_pred_new.sum())
else:
    st.write("Ya has ingresado una fila. No puedes ingresar más datos.")
