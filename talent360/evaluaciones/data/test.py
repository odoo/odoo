
import pandas as pd

# Load the CSV file
df = pd.read_csv('competencia.csv')

# Remove duplicates
# df = df.drop_duplicates()

# change the id col value and add the prefix evaluaciones.pregunta_
# df['pregunta_ids/id'] = df['pregunta_ids/id'].apply(lambda x: ','.join(['evaluaciones.pregunta_' + id for id in x.split(',')]))


# Add id column with the prefix evaluaciones.competencia_n, the id column doesnt exist rn
df.insert(0, 'id', list(map(lambda x: "evaluaciones.competencia_" + str(x) ,range(1, 1 + len(df)))))


# Save the result to a new CSV file
df.to_csv('cometencia_test.csv', index=False)